#!/usr/bin/env python3
"""
Deal registry resolver
======================
Single source of truth for "which deal am I processing, and where is its tape?".

`prep_rmbs.py --deal AVON2` calls into here to turn a short deal id (AVON2) into:
  - the deal's metadata (name, asset_class, status, file patterns), and
  - the absolute path to its loan-level tape on disk.

The registry itself is config/deals.yml. Keeping the lookup logic here (not in
prep_rmbs) means the warehouse loader and RWA engine can resolve the same deal the
same way later, with no copy-pasted path-building.
"""
from __future__ import annotations
import glob
from pathlib import Path
import yaml

# config/deals.yml lives two levels up from this file: src/ingest/deals.py -> repo root.
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "deals.yml"


class DealError(Exception):
    """Raised when a deal can't be resolved (unknown id, awaiting data, tape missing)."""


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    """Read config/deals.yml and return the parsed dict ({'data_root':..., 'deals':[...]})."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def find_deal(deal_id: str, registry: dict | None = None) -> dict:
    """Return the single deal entry whose 'id' matches deal_id (case-insensitive).

    Raises DealError listing the valid ids if there's no match.
    """
    registry = registry or load_registry()
    for deal in registry["deals"]:
        if str(deal["id"]).upper() == deal_id.upper():
            return deal
    valid = ", ".join(d["id"] for d in registry["deals"])
    raise DealError(f"Unknown deal '{deal_id}'. Known deals: {valid}")


def resolve_deal(deal_id: str, registry: dict | None = None) -> tuple[dict, Path]:
    """Resolve a deal id to (deal_dict, absolute_tape_path).

    Looks the deal up in the registry, refuses anything not `status: active`, then globs
    the deal's folder for its `tape_pattern`. Raises DealError if the deal isn't active,
    no tape matches, or the pattern is ambiguous (>1 match) — never silently guesses.

    Returns (deal_dict, Path) where Path is the absolute path to the single matching tape.
    """
    registry = registry or load_registry()
    deal = find_deal(deal_id, registry)

    if deal["status"] != "active":
        raise DealError(
            f"Deal '{deal_id}' is not active (status: {deal.get('status', 'unknown')}). "
            "Drop its tape into the folder and set status: active in config/deals.yml."
        )

    folder = Path(registry["data_root"]) / deal["folder"]
    matches = list(folder.glob(deal["tape_pattern"]))

    if not matches:
        raise DealError(
            f"No tape matching '{deal['tape_pattern']}' found in {folder}."
        )
    if len(matches) > 1:
        raise DealError(
            f"Ambiguous: {len(matches)} tapes match '{deal['tape_pattern']}' in {folder}: "
            f"{[m.name for m in matches]}. Tighten tape_pattern in config/deals.yml."
        )

    return deal, matches[0].resolve()
