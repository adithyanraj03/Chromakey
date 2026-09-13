"""chromakey command line interface.

Subcommands: build, contrast, palette, validate, preview.
Exit codes: 0 ok · 1 data or contrast failure · 2 usage.
"""

import argparse
import json
import sys
from pathlib import Path

from chromakey import __version__
from chromakey import contrast as contrast_mod
from chromakey import emit as emit_mod
from chromakey import palette as palette_mod
from chromakey import preview as preview_mod
from chromakey import tokens as tokens_mod
from chromakey.hexx import ChromakeyError, expand as hex_expand, valid as hex_valid

__all__ = ["main", "build_parser"]

EXAMPLE = '{"color": {"ink": {"$value": "#252524"}}}'
_ALL_FORMATS = ("css", "json", "scss", "tailwind")
_FORMAT_FILES = {
    "css": ".css",
    "scss": ".scss",
    "tailwind": ".tailwind.js",
    "json": ".json",
}


def _common(sub):
    """Per-subcommand --quiet/--json (SUPPRESS so a global flag wins)."""
    sub.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS)
    sub.add_argument("--json", action="store_true", default=argparse.SUPPRESS)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="chromakey",
        description=(
            "A stdlib-only design-token compiler: one JSON in, every "
            "framework out, WCAG-graded."
        ),
    )
    parser.add_argument(
        "--version", action="version", version="chromakey %s" % __version__
    )
    parser.add_argument(
        "--quiet", action="store_true", default=False,
        help="suppress human-readable output",
    )
    parser.add_argument(
        "--json", action="store_true", default=False,
        help="print a machine-readable JSON summary where applicable",
    )

    sub = parser.add_subparsers(dest="command", metavar="command")

    p_build = sub.add_parser("build", help="compile a token file to css/scss/tailwind/json")
    p_build.add_argument("tokens", metavar="TOKENS", help="token file (DTCG or legacy JSON)")
    p_build.add_argument(
        "--format", dest="formats", action="append", choices=sorted(_ALL_FORMATS),
        metavar="FORMAT", help="output format, repeatable (default: all)",
    )
    p_build.add_argument("--out", default="out", metavar="DIR", help="output directory (default: out)")
    p_build.add_argument("--all", action="store_true", help="write every format")
    _common(p_build)

    p_contrast = sub.add_parser("contrast", help="grade color pairs against WCAG AA/AAA")
    p_contrast.add_argument("tokens", metavar="TOKENS")
    p_contrast.add_argument(
        "--pairs", metavar="A,B,A,B", help="explicit pairs of hex values or token names"
    )
    p_contrast.add_argument(
        "--all", action="store_true",
        help="grade every color token against white and black",
    )
    p_contrast.add_argument(
        "--strict", action="store_true", help="exit 1 when any pair fails AA (normal text)"
    )
    _common(p_contrast)

    p_palette = sub.add_parser("palette", help="print an n-step lightness scale for a base hex")
    p_palette.add_argument("hex", metavar="HEX", help="base hex color, e.g. #22AC80")
    p_palette.add_argument("--steps", type=int, default=5, help="number of steps (default: 5)")
    _common(p_palette)

    p_validate = sub.add_parser("validate", help="check token names and hex values")
    p_validate.add_argument("tokens", metavar="TOKENS")
    _common(p_validate)

    p_preview = sub.add_parser("preview", help="write a self-contained preview.html specimen")
    p_preview.add_argument("tokens", metavar="TOKENS")
    p_preview.add_argument(
        "--out", metavar="FILE", help="output file (default: <TOKENS dir>/preview.html)"
    )
    _common(p_preview)

    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    ns = parser.parse_args(argv)
    if not ns.command:
        parser.print_usage(sys.stderr)
        print(
            "error: a command is required (build, contrast, palette, validate, preview)",
            file=sys.stderr,
        )
        return 2
    quiet = bool(getattr(ns, "quiet", False))
    as_json = bool(getattr(ns, "json", False))
    try:
        if ns.command == "build":
            return _cmd_build(ns, quiet, as_json)
        if ns.command == "contrast":
            return _cmd_contrast(ns, quiet, as_json)
        if ns.command == "palette":
            return _cmd_palette(ns, quiet, as_json)
        if ns.command == "validate":
            return _cmd_validate(ns, quiet, as_json)
        return _cmd_preview(ns, quiet, as_json)
    except ChromakeyError as exc:
        print("error: %s" % exc, file=sys.stderr)
        if str(exc).startswith("could not load"):
            print("example: %s" % EXAMPLE, file=sys.stderr)
        return 1


def _load(path_str):
    """Load, format-detect, and alias-resolve a token file (exit 2 if missing)."""
    path = Path(path_str)
    if not path.is_file():
        print("error: no such file: %s" % path_str, file=sys.stderr)
        raise SystemExit(2)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print("error: cannot read %s: %s" % (path_str, exc), file=sys.stderr)
        raise SystemExit(2)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChromakeyError("could not load %s: invalid JSON (%s)" % (path_str, exc))
    if not isinstance(data, dict):
        raise ChromakeyError("could not load %s: top level must be a JSON object" % path_str)
    try:
        return tokens_mod.resolve(tokens_mod.load(data))
    except ChromakeyError as exc:
        raise ChromakeyError("could not load %s: %s" % (path_str, exc))


def _render(fmt, flat):
    if fmt == "css":
        return emit_mod.css(flat)
    if fmt == "scss":
        return emit_mod.scss(flat)
    if fmt == "tailwind":
        return emit_mod.tailwind(flat)
    return emit_mod.json(flat)


def _cmd_build(ns, quiet, as_json):
    flat = _load(ns.tokens)
    formats = list(dict.fromkeys(ns.formats)) if ns.formats else list(_ALL_FORMATS)
    for fmt in formats:
        if fmt not in _FORMAT_FILES:
            print("error: unknown format: %s" % fmt, file=sys.stderr)
            return 2
    out_dir = Path(ns.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(ns.tokens).stem
    written = []
    for fmt in sorted(formats):
        target = out_dir / (stem + _FORMAT_FILES[fmt])
        target.write_text(_render(fmt, flat), encoding="utf-8", newline="\n")
        written.append((fmt, target))
    if as_json:
        print(json.dumps(
            {
                "ok": True,
                "tokens": len(flat),
                "formats": [fmt for fmt, _p in written],
                "files": [str(p) for _f, p in written],
            },
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    elif not quiet:
        for _fmt, target in written:
            print("wrote %s" % target)
        print("%d tokens -> %d files" % (len(flat), len(written)))
    return 0


def _value_of(flat, token):
    if token in flat and isinstance(flat[token], str):
        return flat[token]
    if isinstance(token, str) and token.startswith("#") and hex_valid(token):
        return token
    raise ChromakeyError("pair member %r is not a token name or a hex color" % token)


def _cmd_contrast(ns, quiet, as_json):
    flat = _load(ns.tokens)
    pairs = []
    if ns.pairs:
        values = [v.strip() for v in ns.pairs.split(",") if v.strip()]
        if not values or len(values) % 2 != 0:
            print("error: --pairs needs an even count of values (a,b,a,b)", file=sys.stderr)
            return 2
        for i in range(0, len(values), 2):
            pairs.append(
                (
                    "pair-%d" % (i // 2 + 1),
                    _value_of(flat, values[i]),
                    _value_of(flat, values[i + 1]),
                )
            )
    elif ns.all:
        for name in sorted(flat):
            if not preview_mod.is_color(flat[name]):
                continue
            pairs.append(("%s-on-white" % name, flat[name], "#ffffff"))
            pairs.append(("%s-on-black" % name, flat[name], "#000000"))
    else:
        print("error: contrast needs --all or --pairs", file=sys.stderr)
        return 2

    rows = []
    for name, a, b in pairs:
        try:
            r = contrast_mod.ratio(a, b)
        except ChromakeyError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 1
        rows.append(
            dict(
                {"name": name, "a": a, "b": b, "ratio": round(r, 4)},
                **contrast_mod.verdicts(r)
            )
        )

    failed = [row for row in rows if not row["aa"]]
    if as_json:
        print(json.dumps(
            {"pairs": rows, "failed": len(failed), "total": len(rows)},
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    elif not quiet:
        width = max((len(row["name"]) for row in rows), default=0)
        for row in rows:
            print(
                "%-*s  %s:1  AA %s  AAA %s"
                % (
                    width,
                    row["name"],
                    contrast_mod.format_ratio(row["ratio"]),
                    "✓" if row["aa"] else "✗",
                    "✓" if row["aaa"] else "✗",
                )
            )
    if ns.strict and failed:
        return 1
    return 0


def _cmd_palette(ns, quiet, as_json):
    base = ns.hex.strip()
    if not hex_valid(base):
        print("error: invalid hex color: %s" % ns.hex, file=sys.stderr)
        return 1
    if ns.steps < 1:
        print("error: --steps must be >= 1", file=sys.stderr)
        return 2
    steps = palette_mod.scale(base, ns.steps)
    try:
        canonical = hex_expand(base)
    except ChromakeyError:
        canonical = base.lower()
    if as_json:
        print(json.dumps(
            {"base": canonical, "steps": steps, "n": ns.steps},
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    elif not quiet:
        print("%s -> scale (%d steps, 50 to 900)" % (canonical, ns.steps))
        for step in steps:
            print("  %s" % step)
    return 0


def _cmd_validate(ns, quiet, as_json):
    flat = _load(ns.tokens)
    problems = tokens_mod.validate(flat)
    if as_json:
        print(json.dumps(
            {"ok": not problems, "tokens": len(flat), "problems": problems},
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    elif not quiet:
        if problems:
            for problem in problems:
                print("%s: %s" % (problem["path"], problem["problem"]))
            print("%d problem(s) in %d tokens" % (len(problems), len(flat)))
        else:
            print("ok: %d tokens, names and hex values clean" % len(flat))
    return 1 if problems else 0


def _cmd_preview(ns, quiet, as_json):
    flat = _load(ns.tokens)
    if ns.out:
        target = Path(ns.out)
    else:
        target = Path(ns.tokens).resolve().parent / "preview.html"
    accent = None
    for name in sorted(flat):
        if preview_mod.is_color(flat[name]):
            accent = flat[name]
            break
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(preview_mod.build(flat, accent), encoding="utf-8", newline="\n")
    if as_json:
        print(json.dumps(
            {"ok": True, "tokens": len(flat), "file": str(target)},
            indent=2, sort_keys=True, ensure_ascii=False,
        ))
    elif not quiet:
        print("wrote %s (%d tokens)" % (target, len(flat)))
    return 0
