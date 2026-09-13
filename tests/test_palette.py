"""Palette scales: HSL lightness ramp, neutral bases, clamping."""

import pytest

from chromakey.contrast import luminance
from chromakey.hexx import ChromakeyError
from chromakey.palette import darken, lighten, scale


def test_scale_five_unique_and_light_to_dark():
    steps = scale("#22AC80", 5)
    assert len(steps) == 5
    assert len(set(steps)) == 5
    lum = [luminance(s) for s in steps]
    assert lum == sorted(lum, reverse=True)
    # 50 sits near the top of the ramp (L 0.92), 900 near the bottom (L 0.18)
    assert luminance(steps[0]) > 0.7
    assert luminance(steps[-1]) < 0.2


def test_scale_step_count():
    assert len(scale("#3D96F0", 3)) == 3
    assert len(scale("#3D96F0", 7)) == 7
    assert len(scale("#3D96F0", 1)) == 1


def test_low_saturation_base_is_neutral():
    steps = scale("#808080", 5)
    for step in steps:
        r, g, b = (int(step[i:i + 2], 16) for i in (1, 3, 5))
        assert r == g == b
    assert len(set(steps)) == 5


def test_scale_hex_canonical_lowercase():
    for step in scale("#EAF4F0", 5):
        assert step == step.lower()
        assert len(step) == 7
        assert step.startswith("#")


def test_lighten_darken_move_lightness():
    assert lighten("#000000", 0.5) == "#808080"
    assert darken("#808080", 0.5) == "#000000"


def test_lighten_clamps_at_white():
    assert lighten("#000000", 1.0) == "#ffffff"
    assert lighten("#ffffff", 0.5) == "#ffffff"


def test_darken_clamps_at_black():
    assert darken("#ffffff", 1.0) == "#000000"
    assert darken("#000000", 0.5) == "#000000"


def test_alpha_rejected_in_palette():
    with pytest.raises(ChromakeyError, match="alpha unsupported"):
        scale("#FF000080", 5)


def test_bad_step_count_rejected():
    with pytest.raises(ChromakeyError):
        scale("#22AC80", 0)
