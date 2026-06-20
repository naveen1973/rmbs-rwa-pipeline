"""
Contract tests for the deal registry resolver (src/ingest/deals.py).

These define what `resolve_deal` must do — write the function until they pass:

    pytest tests/test_deals.py -v

They build a FAKE registry over a pytest tmp_path, so they don't depend on the real
OneDrive tapes existing. `find_deal` / `load_registry` are already implemented; the
`resolve_deal` tests are the target for your part.
"""
import pytest

from src.ingest.deals import find_deal, resolve_deal, DealError


@pytest.fixture
def fake_registry(tmp_path):
    """A registry pointing at a temp data_root with controlled folder/file contents.

    Layout created under tmp_path:
        Avon/AF2_Monthly_Data_Tape_Oct_2020.xlsx   (exactly one tape  -> happy path)
        Bletchley Park/                              (empty, awaiting_data)
        Ambiguous/two .xlsx files                    (active, >1 match -> must error)
        Missing/                                     (active, 0 matches -> must error)
    """
    (tmp_path / "Avon").mkdir()
    (tmp_path / "Avon" / "AF2_Monthly_Data_Tape_Oct_2020.xlsx").write_text("x")

    (tmp_path / "Bletchley Park").mkdir()

    (tmp_path / "Ambiguous").mkdir()
    (tmp_path / "Ambiguous" / "Tape_A.xlsx").write_text("x")
    (tmp_path / "Ambiguous" / "Tape_B.xlsx").write_text("x")

    (tmp_path / "Missing").mkdir()

    return {
        "data_root": str(tmp_path),
        "deals": [
            {"id": "AVON2", "folder": "Avon", "status": "active",
             "tape_pattern": "*Data_Tape*.xlsx"},
            {"id": "BLETCHLEY", "folder": "Bletchley Park", "status": "awaiting_data",
             "tape_pattern": "*.xlsx"},
            {"id": "AMBIG", "folder": "Ambiguous", "status": "active",
             "tape_pattern": "*.xlsx"},
            {"id": "NOTAPE", "folder": "Missing", "status": "active",
             "tape_pattern": "*.xlsx"},
        ],
    }


# ---- find_deal (already implemented) ----------------------------------------

def test_find_deal_matches_case_insensitively(fake_registry):
    assert find_deal("avon2", fake_registry)["id"] == "AVON2"


def test_find_deal_unknown_id_raises(fake_registry):
    with pytest.raises(DealError):
        find_deal("NOPE", fake_registry)


# ---- resolve_deal (your part) -----------------------------------------------

def test_resolve_deal_returns_deal_and_existing_tape_path(fake_registry):
    deal, tape = resolve_deal("AVON2", fake_registry)
    assert deal["id"] == "AVON2"
    assert tape.name == "AF2_Monthly_Data_Tape_Oct_2020.xlsx"
    assert tape.is_absolute()
    assert tape.exists()


def test_resolve_deal_awaiting_data_raises(fake_registry):
    # Status guard: don't glob an empty folder for a deal with no data yet.
    with pytest.raises(DealError):
        resolve_deal("BLETCHLEY", fake_registry)


def test_resolve_deal_no_tape_raises(fake_registry):
    with pytest.raises(DealError):
        resolve_deal("NOTAPE", fake_registry)


def test_resolve_deal_ambiguous_match_raises(fake_registry):
    # Two files match the pattern -> must fail loudly, not silently pick one.
    with pytest.raises(DealError):
        resolve_deal("AMBIG", fake_registry)
