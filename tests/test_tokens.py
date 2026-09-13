"""tokens.load / resolve / validate + hexx primitives."""

import json

import pytest

from chromakey import tokens
from chromakey.hexx import ChromakeyError, expand, valid


def test_dtcg_flatten_three_levels(dtcg):
    flat = tokens.load(dtcg)
    assert flat["color-ink"] == "#252524"
    assert flat["color-green"] == "#22AC80"
    assert flat["color-paper"] == "#DFDFDF"
    assert flat["space-base"] == "4px"


def test_dtcg_flatten_deep_nesting():
    data = {"color": {"scale": {"green": {"500": {"$value": "#22AC80"}}}}}
    assert tokens.load(data) == {"color-scale-green-500": "#22AC80"}


def test_legacy_flat_pass(legacy):
    assert tokens.load(legacy) == {
        "color-ink": "#252524",
        "color-paper": "#DFDFDF",
        "space-base": "4px",
    }


def test_legacy_figma_value_leaves():
    data = {"color": {"bg": {"value": "#FFFFFF", "value-extra-ignored": None}}}
    # {"value": ...} with only-$-or-value keys is a Figma-style leaf;
    # the extra non-$ key makes it a group, so use the pure shape:
    data = {"color": {"bg": {"value": "#FFFFFF"}}}
    assert tokens.load(data) == {"color-bg": "#FFFFFF"}


def test_mixed_formats_raise():
    data = {"color": {"a": "#FFFFFF", "b": {"$value": "#000000"}}}
    with pytest.raises(ChromakeyError, match="mixed formats"):
        tokens.load(data)


def test_load_accepts_json_text(dtcg):
    assert tokens.load(json.dumps(dtcg)) == tokens.load(dtcg)


def test_unknown_dollar_props_tolerated():
    data = {
        "color": {
            "ink": {
                "$value": "#111111",
                "$type": "color",
                "$extends": {"$value": "#000000"},
            }
        }
    }
    assert tokens.load(data) == {"color-ink": "#111111"}


def test_load_invalid_json_raises():
    with pytest.raises(ChromakeyError, match="could not parse JSON"):
        tokens.load("{not json")


def test_alias_resolve_two_deep():
    flat = {
        "color-base": "#111111",
        "color-mid": "{color-base}",
        "color-final": "{color-mid}",
    }
    resolved = tokens.resolve(flat)
    assert resolved["color-final"] == "#111111"
    assert resolved["color-mid"] == "#111111"


def test_alias_dotted_reference():
    flat = {"color-ink": "#252524", "alias-ink": "{color.ink}"}
    assert tokens.resolve(flat)["alias-ink"] == "#252524"


def test_alias_cycle_raises():
    flat = {"a-first": "{a-second}", "a-second": "{a-first}"}
    with pytest.raises(ChromakeyError, match="alias cycle"):
        tokens.resolve(flat)


def test_alias_missing_target_raises():
    flat = {"a-first": "{missing.token}"}
    with pytest.raises(ChromakeyError, match="missing.token"):
        tokens.resolve(flat)


def test_multi_ref_alias_rejected():
    flat = {
        "a-first": "{a-second,a-third}",
        "a-second": "#111111",
        "a-third": "#222222",
    }
    with pytest.raises(ChromakeyError):
        tokens.resolve(flat)


def test_validate_catches_bad_name():
    problems = tokens.validate({"bad_name": "#252524"})
    assert any(p["path"] == "bad_name" and "kebab-case" in p["problem"] for p in problems)


def test_validate_catches_bad_hex():
    problems = tokens.validate({"color-bad": "#GGG"})
    assert any(p["path"] == "color-bad" and "hex" in p["problem"] for p in problems)


def test_validate_min_two_segments():
    problems = tokens.validate({"ink": "#252524"})
    assert any(p["path"] == "ink" and "2 segments" in p["problem"] for p in problems)


def test_validate_clean():
    assert tokens.validate({"color-ink": "#252524", "space-base": "4px"}) == []


def test_hex_expand_shorthand():
    assert expand("#F00") == "#ff0000"
    assert expand("#abc") == "#aabbcc"
    assert expand("#ABCDEF") == "#abcdef"


def test_hex_invalid_rejected():
    assert not valid("GGG")
    assert not valid("#12345")
    assert not valid("blue")
    assert not valid(None)
    assert valid("#F00")
    assert valid("#ff0000")
    assert valid("#ff000080")
