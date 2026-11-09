"""Name-safety tests. Real names never appear in this repo: they are read from the local,
git-ignored legacy/real_names.json; tests that need them skip when it is absent."""
from pathlib import Path

import pytest

from helivara import names
from helivara.names import FICTIONAL_BRANDS, FICTIONAL_PLANTS, find_forbidden

REAL = names.load_real_names(missing_ok=True)
needs_real = pytest.mark.skipif(REAL is None, reason="legacy/real_names.json not present")


@needs_real
def test_find_forbidden_flags_every_real_name():
    for real in REAL.forbidden:
        assert find_forbidden(f"text {real} text") == [real], real


@needs_real
def test_find_forbidden_is_case_insensitive():
    real = next(iter(REAL.brand_map))
    assert find_forbidden(real.upper()) == [real.upper()]


def test_find_forbidden_clean_on_fictional_names():
    assert find_forbidden(" ".join(FICTIONAL_BRANDS + FICTIONAL_PLANTS)) == []
    assert find_forbidden("vessels, Zyvanta at Valmora") == []


@needs_real
def test_rename_maps_to_fictional():
    text = " / ".join(REAL.brand_map) + " / " + " / ".join(REAL.launch_id_map)
    out = names.rename(text)
    assert find_forbidden(out) == []
    assert "Zyvanta" in out and "ZYV-001" in out and "Faringel" in out


@needs_real
def test_fictional_lists_match_maps():
    assert sorted(REAL.brand_map.values()) == sorted(FICTIONAL_BRANDS)
    assert sorted(REAL.plant_map.values()) == sorted(FICTIONAL_PLANTS)


def test_repo_module_contains_no_real_names():
    src = Path(names.__file__).read_text(encoding="utf-8")
    assert find_forbidden(src) == []
