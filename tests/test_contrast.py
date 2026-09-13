"""WCAG contrast math: luminance, unrounded ratio, verdict boundaries."""

import pytest

from chromakey.contrast import format_ratio, luminance, ratio, verdicts
from chromakey.hexx import ChromakeyError


def test_black_white_is_21():
    assert abs(ratio("#000000", "#FFFFFF") - 21.0) < 1e-9
    assert format_ratio(ratio("#000000", "#FFFFFF")) == "21.00"


def test_ratio_symmetric():
    assert ratio("#767676", "#FFFFFF") == ratio("#FFFFFF", "#767676")


def test_luminance_extremes():
    assert luminance("#FFFFFF") == pytest.approx(1.0)
    assert luminance("#000000") == pytest.approx(0.0)


def test_luminance_mid_gray():
    # 128/255 -> ((0.50196 + 0.055) / 1.055) ** 2.4 ~= 0.2159
    assert luminance("#808080") == pytest.approx(0.2159, abs=1e-3)


def test_767676_passes_aa_on_white():
    r = ratio("#767676", "#FFFFFF")
    assert r == pytest.approx(4.54, abs=0.005)
    assert verdicts(r)["aa"] is True
    assert format_ratio(r) == "4.54"


def test_777777_fails_aa_on_white():
    r = ratio("#777777", "#FFFFFF")
    assert r == pytest.approx(4.48, abs=0.005)
    assert verdicts(r)["aa"] is False
    assert verdicts(r)["aa_large"] is True
    assert format_ratio(r) == "4.48"


def test_verdict_boundaries():
    assert verdicts(4.495)["aa"] is False
    assert verdicts(4.5)["aa"] is True
    assert verdicts(2.99)["aa_large"] is False
    assert verdicts(3.0)["aa_large"] is True
    assert verdicts(6.99)["aaa"] is False
    assert verdicts(7.0)["aaa"] is True


def test_display_rounds_but_verdict_uses_unrounded():
    # 4.496 displays as 4.50 but must NOT pass AA: verdicts run on the
    # unrounded ratio, never on the displayed string.
    r = 4.496
    assert format_ratio(r) == "4.50"
    assert verdicts(r)["aa"] is False


def test_alpha_rejected():
    with pytest.raises(ChromakeyError, match="alpha unsupported"):
        ratio("#FF0000FF", "#FFFFFF")
    with pytest.raises(ChromakeyError, match="alpha unsupported"):
        luminance("#FF000080")


def test_invalid_hex_rejected():
    with pytest.raises(ChromakeyError):
        ratio("#GGG", "#FFFFFF")
