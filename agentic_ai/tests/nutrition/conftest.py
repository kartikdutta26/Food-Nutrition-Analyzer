"""All modified USDA payloads in tests are synthetic fault cases, not snapshots."""

import copy
import json
from decimal import Decimal
from pathlib import Path

import pytest

from agentic_ai.providers.usda import SnapshotProvider
from agentic_ai.schemas.food import FoodItem, FoodUnderstandingResult


@pytest.fixture
def snapshot():
    return SnapshotProvider()


@pytest.fixture
def raw_usda():
    records = json.loads((Path(__file__).parents[2] / "data/usda/foods.json").read_text(encoding="utf-8"), parse_float=Decimal)
    return lambda fdc_id=168878: copy.deepcopy(next(r for r in records if r["fdcId"] == fdc_id))


@pytest.fixture
def meal():
    def make(*foods):
        return FoodUnderstandingResult(status="success" if foods else "no_food", foods=list(foods), questions=[])
    return make


@pytest.fixture
def item():
    def make(name="white rice", quantity=150, unit="g", preparation="cooked", source_text=None, **changes):
        return FoodItem(name=name, quantity=float(quantity) if quantity is not None else None, unit=unit, preparation=preparation, source_text=source_text or f"{quantity} {unit} {preparation or ''} {name}", quantity_text=str(quantity) if quantity is not None else None, issues=[], **changes)
    return make
