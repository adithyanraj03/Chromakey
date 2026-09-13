"""Shared fixtures: DTCG dict, legacy dict, sample file paths."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def dtcg():
    return {
        "color": {
            "green": {"$value": "#22AC80", "$type": "color"},
            "ink": {"$value": "#252524", "$type": "color", "$description": "primary text"},
            "paper": {"$value": "#DFDFDF", "$type": "color"},
        },
        "space": {
            "base": {"$value": "4px"},
        },
    }


@pytest.fixture
def legacy():
    return {
        "color": {"ink": "#252524", "paper": "#DFDFDF"},
        "space": {"base": "4px"},
    }


@pytest.fixture
def sample_tokens():
    return ROOT / "sample" / "tokens.json"


@pytest.fixture
def sample_legacy():
    return ROOT / "sample" / "legacy.json"
