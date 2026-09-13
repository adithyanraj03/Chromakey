"""WCAG contrast math — always on the UNROUNDED ratio.

sRGB gamma linearization (8-bit channel c: c <= 0.04045 -> c/12.92,
else ((c + 0.055) / 1.055) ** 2.4), relative luminance
L = 0.2126 R + 0.7152 G + 0.0722 B, ratio = (L_hi + 0.05) / (L_lo + 0.05).
Verdicts compare the unrounded ratio, so 4.495 never display-passes as
4.50; display uses ``format_ratio`` (2 decimal places) only.
"""

from chromakey.hexx import ChromakeyError, expand, has_alpha

__all__ = ["luminance", "ratio", "verdicts", "format_ratio"]

_AA = 4.5
_AA_LARGE = 3.0
_AAA = 7.0


def _linearize(channel):
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_color):
    """Relative luminance (0..1) of an opaque hex color, sRGB-linearized."""
    if has_alpha(hex_color):
        raise ChromakeyError("alpha unsupported: %s" % hex_color)
    hex6 = expand(hex_color)
    r, g, b = (int(hex6[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    r = _linearize(r)
    g = _linearize(g)
    b = _linearize(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(color_a, color_b):
    """WCAG contrast ratio of two opaque hex colors, UNROUNDED."""
    la = luminance(color_a)
    lb = luminance(color_b)
    hi, lo = (la, lb) if la >= lb else (lb, la)
    return (hi + 0.05) / (lo + 0.05)


def verdicts(r):
    """Pass/fail against WCAG thresholds, compared on the UNROUNDED ratio."""
    return {
        "aa": r >= _AA,
        "aa_large": r >= _AA_LARGE,
        "aaa": r >= _AAA,
    }


def format_ratio(r):
    """Display form: exactly 2 decimal places. Verdicts never use this."""
    return "%.2f" % r
