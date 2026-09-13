"""Self-contained preview.html specimen.

Single file, no JavaScript, no external references (the string
"http" never appears), Atelier styling inlined as plain CSS values
copied from the token subset. Every token name is rendered; color
tokens get a swatch with an AA badge vs white and vs black; one
accent gets a 5-step ramp row.
"""

from chromakey import __version__
from chromakey.contrast import ratio, verdicts
from chromakey.hexx import has_alpha, valid as _hex_valid
from chromakey.palette import scale

__all__ = ["build", "is_color"]


def _escape(text):
    """Minimal HTML escaping (stdlib allowlist avoids the html module)."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )

_CSS = """
:root {
  --paper: #dfdfdf;
  --surface: #dfdfdb;
  --ink: #252524;
  --ink-2: #676662;
  --ink-3: #94938c;
  --hairline: #dcdad1;
  --hairline-strong: #d4d2c8;
  --serif: Georgia, "Times New Roman", Times, serif;
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 40px;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--sans);
  font-size: 15px;
  line-height: 1.65;
}
main { max-width: 1080px; margin: 0 auto; }
h1 { font-family: var(--serif); font-size: 30px; font-weight: 700; margin: 0 0 4px; }
.meta { color: var(--ink-2); font-size: 12px; margin: 0 0 8px; }
h2 {
  font-family: var(--serif);
  font-size: 20px;
  font-weight: 700;
  margin: 28px 0 12px;
}
.grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.swatch {
  border: 1px solid var(--hairline-strong);
  border-radius: 8px;
  overflow: hidden;
  background: var(--surface);
}
.swatch .chip { height: 56px; }
.swatch .row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  font-size: 11px;
}
.swatch .name { font-weight: 600; word-break: break-all; }
.swatch .hex { color: var(--ink-2); white-space: nowrap; }
.badge {
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10px;
  white-space: nowrap;
}
.badge.pass { background: #13785e; color: #ffffff; }
.badge.fail { background: #a74221; color: #ffffff; }
.ramp {
  display: flex;
  border: 1px solid var(--hairline-strong);
  border-radius: 8px;
  overflow: hidden;
}
.ramp div { flex: 1; height: 44px; }
.ramp-labels { display: flex; margin-top: 4px; }
.ramp-labels span { flex: 1; text-align: center; font-size: 10px; color: var(--ink-2); }
dl.other { margin: 0; }
dl.other > div {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  border-bottom: 1px solid var(--hairline);
  font-size: 13px;
}
dl.other dt { font-weight: 600; min-width: 240px; }
dl.other dd { margin: 0; color: var(--ink-2); }
footer { margin-top: 32px; font-size: 11px; color: var(--ink-2); }
"""


def is_color(value):
    """True when value is an opaque, strict hex color."""
    return (
        isinstance(value, str)
        and value.strip().startswith("#")
        and _hex_valid(value)
        and not has_alpha(value)
    )


def _badge(fg, bg, label):
    verdict = verdicts(ratio(fg, bg))
    ok = verdict["aa"]
    return '<span class="badge %s">%s AA %s</span>' % (
        "pass" if ok else "fail",
        label,
        "✓" if ok else "✗",
    )


def build(flat, scale_sample=None):
    """Render the preview.html document as one string.

    ``scale_sample`` is the hex base for the ramp row; when omitted the
    first (sorted) color token is used. Output is deterministic: no
    timestamps, sorted tokens, no scripts, no external references.
    """
    colors = sorted((n, flat[n]) for n in flat if is_color(flat[n]))
    others = sorted((n, flat[n]) for n in flat if not is_color(flat[n]))
    accent = scale_sample
    if accent is None and colors:
        accent = colors[0][1]

    swatches = []
    for name, value in colors:
        swatches.append(
            '      <div class="swatch">\n'
            '        <div class="chip" style="background:%s"></div>\n'
            '        <div class="row">\n'
            '          <span class="name">%s</span>\n'
            '          <span class="hex">%s</span>\n'
            '          <span>%s %s</span>\n'
            '        </div>\n'
            '      </div>'
            % (
                value.strip().lower(),
                _escape(name),
                value.strip().lower(),
                _badge(value, "#ffffff", "white"),
                _badge(value, "#000000", "black"),
            )
        )

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Atelier tokens — preview</title>",
        "<style>",
        _CSS,
        "</style>",
        "</head>",
        "<body>",
        "<main>",
        "  <h1>Atelier tokens — preview</h1>",
        '  <p class="meta">generated by chromakey %s · %d tokens · '
        "single file, no scripts, no external assets</p>" % (__version__, len(flat)),
        "  <section>",
        "    <h2>Color tokens · %d</h2>" % len(colors),
        '    <div class="grid">',
    ]
    parts.extend(swatches)
    parts.extend(["    </div>", "  </section>"])

    if accent is not None:
        steps = scale(accent, 5)
        ramp_parts = ["  <section>", "    <h2>Scale · %s · 50 → 900</h2>" % _escape(
            accent.strip().lower()
        ), "    <div class=\"ramp\">"]
        ramp_parts.extend('      <div style="background:%s"></div>' % s for s in steps)
        ramp_parts.append("    </div>")
        ramp_parts.append('    <div class="ramp-labels">')
        ramp_parts.extend(
            "      <span>%s</span>" % label
            for label in ("50", "300", "500", "700", "900")
        )
        ramp_parts.extend(["    </div>", "  </section>"])
        parts.extend(ramp_parts)

    if others:
        other_rows = [
            "      <div><dt>%s</dt><dd>%s</dd></div>"
            % (_escape(name), _escape(str(value)))
            for name, value in others
        ]
        parts.extend(
            [
                "  <section>",
                "    <h2>Other tokens · %d</h2>" % len(others),
                '    <dl class="other">',
            ]
        )
        parts.extend(other_rows)
        parts.extend(["    </dl>", "  </section>"])

    parts.extend(
        [
            "  <footer>Contrast badges grade each token against white and black "
            "on the unrounded WCAG ratio (AA = 4.5:1).</footer>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )
    return "\n".join(parts) + "\n"
