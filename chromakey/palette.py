"""Palette scales via an HSL lightness ramp.

``scale`` emits n canonical lowercase ``#rrggbb`` steps, light (50) to
dark (900), with lightness ramping 0.92 -> 0.18. Saturation is
preserved, except for low-saturation bases (S < 8%), which get a
neutral gray ramp to avoid hue jitter. ``lighten``/``darken`` shift
HSL lightness by an absolute amount (0..1), clamped.
"""

import colorsys

from chromakey.hexx import ChromakeyError, expand, has_alpha

__all__ = ["scale", "lighten", "darken"]

_L_TOP = 0.92
_L_BOTTOM = 0.18
_NEUTRAL_SAT = 0.08


def _hsl(hex_color):
    if has_alpha(hex_color):
        raise ChromakeyError("alpha unsupported: %s" % hex_color)
    v = expand(hex_color)
    r, g, b = (int(v[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h, s, l


def _hex_from_hsl(h, s, l):
    s = min(1.0, max(0.0, s))
    l = min(1.0, max(0.0, l))
    r, g, b = colorsys.hls_to_rgb(h % 1.0, l, s)
    return "#%02x%02x%02x" % (
        int(round(r * 255)),
        int(round(g * 255)),
        int(round(b * 255)),
    )


def _lightnesses(n):
    if not isinstance(n, int) or n <= 0:
        raise ChromakeyError("step count must be a positive integer")
    if n == 1:
        return [0.55]
    step = (_L_TOP - _L_BOTTOM) / (n - 1)
    return [_L_TOP - step * i for i in range(n)]


def scale(base, n=5):
    """n canonical hex steps, light (50) to dark (900)."""
    h, s, _l = _hsl(base)
    if s < _NEUTRAL_SAT:
        s = 0.0
    return [_hex_from_hsl(h, s, l) for l in _lightnesses(n)]


def _shift(hex_color, delta):
    h, s, l = _hsl(hex_color)
    return _hex_from_hsl(h, s, l + delta)


def lighten(hex_color, amount):
    """Raise HSL lightness by amount (0..1), clamped at 1.0."""
    return _shift(hex_color, amount)


def darken(hex_color, amount):
    """Lower HSL lightness by amount (0..1), clamped at 0.0."""
    return _shift(hex_color, -amount)
