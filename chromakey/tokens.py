"""Token loading (format detection), alias resolution, and validation.

``load`` normalizes a DTCG or legacy token tree into a flat
``{name: value}`` dict with CTI names (``category-type-item``).
``resolve`` walks ``{path.to.token}`` aliases to fixed point with cycle
and missing-target detection. ``validate`` checks names and hex values.
"""

import json
import re

from chromakey.hexx import ChromakeyError, valid as _hex_valid

__all__ = ["load", "resolve", "validate"]

_ALIAS_RE = re.compile(r"^\{([A-Za-z0-9._-]+)\}$")
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def load(obj_or_text):
    """Normalize a token tree to a flat ``{name: value}`` dict.

    Accepts a parsed JSON object or raw JSON text. Format detection:
    any ``$value`` leaf means DTCG (nested groups are flattened to
    ``a-b-c``); files with no ``$value`` are legacy (plain leaves).
    Mixing the two inside a single group raises ChromakeyError
    ("mixed formats ..."); plain leaves living in their own groups
    (for example a ``meta`` group next to DTCG groups) are tolerated
    and emitted as plain tokens. Unknown ``$``-properties
    (``$type``, ``$description``, ...) are tolerated. Legacy
    Figma-style ``{"value": "..."}`` leaves are accepted too.
    """
    if isinstance(obj_or_text, str):
        try:
            data = json.loads(obj_or_text)
        except json.JSONDecodeError as exc:
            raise ChromakeyError("could not parse JSON: %s" % exc)
    else:
        data = obj_or_text
    if not isinstance(data, dict):
        raise ChromakeyError("token tree must be a JSON object at the top level")

    mode = _classify(data)
    out = {}
    if mode == "dtcg":
        _walk_dtcg(data, [], out)
    else:
        _walk_legacy(data, [], out)
    if not out:
        raise ChromakeyError("token file contains no tokens")
    return out


def _classify(root):
    """Return "dtcg" or "legacy"; raise when one group mixes both formats.

    A file is DTCG when any leaf token uses ``$value``. Mixing is judged
    per group node: a node that has both plain scalar children and
    ``$value`` leaf children is ambiguous and rejected. Plain leaves in
    groups of their own (e.g. a ``meta`` group next to DTCG groups) are
    tolerated.
    """
    state = {"dtcg": 0}

    def walk(node):
        dt_leaf = 0
        plain = 0
        for key, value in node.items():
            if key.startswith("$"):
                continue
            if isinstance(value, dict):
                if "$value" in value:
                    dt_leaf += 1
                    state["dtcg"] += 1
                else:
                    walk(value)
            else:
                plain += 1
        if dt_leaf and plain:
            raise ChromakeyError(
                "mixed formats: some tokens use $value (DTCG) and some are plain "
                "values (legacy); convert the file to a single format"
            )

    walk(root)
    return "dtcg" if state["dtcg"] else "legacy"


def _walk_dtcg(node, prefix, out):
    for key in sorted(node):
        if key.startswith("$"):
            continue
        value = node[key]
        path = prefix + [key]
        if isinstance(value, dict):
            if "$value" in value and not any(not k.startswith("$") for k in value):
                # DTCG leaf: {"$value": ..., "$type": ...}
                out["-".join(path)] = value["$value"]
            else:
                _walk_dtcg(value, path, out)
        else:
            # Plain leaf inside a DTCG file (e.g. a "meta" group):
            # emitted as a plain token.
            out["-".join(path)] = value


def _walk_legacy(node, prefix, out):
    for key in sorted(node):
        if key.startswith("$"):
            continue
        value = node[key]
        path = prefix + [key]
        if isinstance(value, dict):
            if set(k for k in value if not k.startswith("$")) == {"value"}:
                # Figma-style legacy leaf: {"value": "#fff"}
                out["-".join(path)] = value["value"]
                continue
            _walk_legacy(value, path, out)
        else:
            out["-".join(path)] = value


def resolve(flat):
    """Resolve ``{path.to.token}`` aliases to their final values.

    A value is an alias only when it is exactly one ``{ref}`` (single
    reference; multi-refs like ``{a,b}`` are rejected). References may
    use dot or hyphen separators and may point at other aliases
    (resolved to fixed point). Cycles and missing targets raise
    ChromakeyError naming the offending path.
    """
    resolved = {}
    stack = []

    def ref_candidates(ref):
        seen = []
        for candidate in (ref, ref.replace(".", "-"), ref.replace("-", ".")):
            if candidate not in seen:
                seen.append(candidate)
        return seen

    def get(name):
        if name in resolved:
            return resolved[name]
        if name in stack:
            start = stack.index(name)
            raise ChromakeyError("alias cycle: %s" % " -> ".join(stack[start:] + [name]))
        if name not in flat:
            raise ChromakeyError(
                "missing alias target %s (referenced by %s)"
                % (name, " -> ".join(stack) if stack else "top level")
            )
        stack.append(name)
        try:
            value = flat[name]
            if isinstance(value, str):
                stripped = value.strip()
                match = _ALIAS_RE.match(stripped)
                if match is not None:
                    ref = match.group(1)
                    for candidate in ref_candidates(ref):
                        if candidate in flat:
                            value = get(candidate)
                            break
                    else:
                        raise ChromakeyError(
                            "missing alias target %s (referenced by %s)" % (ref, name)
                        )
                elif "{" in stripped and "}" in stripped:
                    raise ChromakeyError(
                        "invalid alias %r in token %s: expected a single "
                        "{path.to.token}" % (value, name)
                    )
        finally:
            stack.pop()
        resolved[name] = value
        return value

    for name in sorted(flat):
        get(name)
    return {name: resolved[name] for name in sorted(resolved)}


def validate(flat):
    """Check names (kebab-case, at least 2 segments) and hex values.

    Returns a list of ``{"path": name, "problem": message}`` dicts
    sorted by path; an empty list means the file is clean. Values that
    look like hex colors (start with ``#``) must be strict hex.
    """
    problems = []
    for name in sorted(flat):
        if not _NAME_RE.match(name):
            problems.append(
                {
                    "path": name,
                    "problem": (
                        "name must be kebab-case (lowercase a-z, 0-9, single "
                        "hyphens, no leading $, no double hyphens)"
                    ),
                }
            )
            continue
        if name.count("-") < 1:
            problems.append(
                {
                    "path": name,
                    "problem": "name must have at least 2 segments (category-item, a-b)",
                }
            )
        value = flat[name]
        if isinstance(value, str) and value.strip().startswith("#") and not _hex_valid(value):
            problems.append(
                {"path": name, "problem": "invalid hex color: %s" % value}
            )
    return problems
