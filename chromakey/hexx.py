"""Hex color primitives — the leaf module every other module builds on.

Also the single home of ChromakeyError, so leaf-level failures (bad
hex, alpha where opaque is required) share one exception type.
"""

import re

__all__ = ["ChromakeyError", "valid", "has_alpha", "expand"]

_HEX3 = re.compile(r"^#[0-9a-fA-F]{3}$")
_HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")
_HEX8 = re.compile(r"^#[0-9a-fA-F]{8}$")


class ChromakeyError(ValueError):
    """Any user-facing chromakey failure (bad input, alias cycles, bad data)."""


def valid(value):
    """Return True when value is a strict hex color string.

    Accepts #RGB, #RRGGBB, and #RRGGBBAA. Everything else — named
    colors, var(), rgb(), bare numbers — is rejected. Alpha is accepted
    as *valid hex* but warned against by contrast/palette, where it is
    unsupported.
    """
    if not isinstance(value, str):
        return False
    value = value.strip()
    return bool(_HEX3.match(value) or _HEX6.match(value) or _HEX8.match(value))


def has_alpha(value):
    """True when value is an 8-digit hex color (#RRGGBBAA)."""
    if not isinstance(value, str):
        return False
    return bool(_HEX8.match(value.strip()))


def expand(value):
    """Normalize a hex color to canonical lowercase #rrggbb.

    Expands the #RGB shorthand and lowercases #RRGGBB. Rejects non-hex
    input, and rejects 8-digit alpha colors: WCAG contrast is undefined
    with alpha, so opaque-only callers must never see one through here.
    """
    if not isinstance(value, str):
        raise ChromakeyError("hex color expected, got %r" % (value,))
    v = value.strip()
    if _HEX8.match(v):
        raise ChromakeyError(
            "alpha unsupported: %s (WCAG contrast requires an opaque color)" % v
        )
    if _HEX3.match(v):
        v = "#" + "".join(ch * 2 for ch in v[1:])
    if not _HEX6.match(v):
        raise ChromakeyError("invalid hex color: %s" % value)
    return v.lower()
