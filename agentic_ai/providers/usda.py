"""Provider interfaces allow offline tests and live lookup to share calculations."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from agentic_ai.clients.usda_client import USDAClient
from agentic_ai.nutrition_errors import FoodNotFoundError, SnapshotError, USDAResponseError
from agentic_ai.schemas.nutrition import FoodCandidate, NutritionRecord, SearchResults
from agentic_ai.tools.usda_normalization import normalize_usda_food


class NutritionProvider(Protocol):
    def search(self, query: str) -> SearchResults: ...
    def get(self, fdc_id: int) -> NutritionRecord: ...


class SnapshotProvider:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory is not None else Path(__file__).parents[1] / "data" / "usda"
        try:
            manifest = json.loads((self.directory / "manifest.json").read_text(encoding="utf-8"))
            raw = (self.directory / "foods.json").read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest["sha256"]:
                raise ValueError("Snapshot checksum mismatch")
            foods = json.loads(raw, parse_float=Decimal)
            if not isinstance(foods, list):
                raise ValueError("Snapshot must contain food details")
            self.records = {}
            for food in foods:
                record = normalize_usda_food(food, provider="usda_snapshot", retrieved_at=manifest["retrieved_at"], snapshot_sha256=manifest["sha256"])
                if record.provenance.fdc_id in self.records:
                    raise ValueError("Duplicate food ID")
                self.records[record.provenance.fdc_id] = record
            expected = {item["fdc_id"]: item for item in manifest["records"]}
            if set(expected) != set(self.records):
                raise ValueError("Manifest ID mismatch")
            for fdc_id, record in self.records.items():
                if expected[fdc_id]["description"] != record.provenance.description or expected[fdc_id]["data_type"] != record.provenance.data_type:
                    raise ValueError("Manifest identity mismatch")
        except (OSError, ValueError, KeyError, TypeError, USDAResponseError):
            raise SnapshotError("USDA snapshot is missing, invalid, or failed its integrity check.") from None

    def search(self, query):
        # Intentionally expose the entire small catalog; the shared matcher filters it.
        return SearchResults(candidates=[FoodCandidate(fdc_id=r.provenance.fdc_id, description=r.provenance.description, data_type=r.provenance.data_type) for r in self.records.values()], exhaustive=True, scope=f"offline USDA snapshot: {len(self.records)} records; not the complete USDA catalog")

    def get(self, fdc_id):
        if fdc_id not in self.records:
            raise FoodNotFoundError("Food ID is not available in this offline USDA snapshot.")
        return self.records[fdc_id].model_copy(deep=True)


class LiveUSDAProvider:
    def __init__(self, client=None):
        self.client = client if client is not None else USDAClient()

    def search(self, query):
        raw = self.client.search(query)
        try:
            foods, total = raw["foods"], raw["totalHits"]
            if not isinstance(foods, list) or type(total) is not int or total < len(foods):
                raise ValueError("Invalid search counts")
            candidates = []
            for food in foods:
                if not isinstance(food, dict) or food.get("dataType") not in {"Foundation", "SR Legacy", "Survey (FNDDS)"}:
                    raise ValueError("Invalid candidate metadata")
                candidates.append(FoodCandidate(fdc_id=food["fdcId"], description=food["description"], data_type=food["dataType"]))
            if len({f.fdc_id for f in candidates}) != len(candidates):
                raise ValueError("Duplicate candidate IDs")
            return SearchResults(candidates=candidates, exhaustive=total <= len(foods), scope=f"live USDA search: {len(foods)} of {total} results retrieved")
        except (ValueError, TypeError, KeyError, AttributeError, ValidationError):
            raise USDAResponseError("USDA returned an invalid search response.") from None

    def get(self, fdc_id):
        raw, retrieved_at = self.client.food(fdc_id)
        return normalize_usda_food(raw, provider="usda_live", retrieved_at=retrieved_at, expected_id=fdc_id)
