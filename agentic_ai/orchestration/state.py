"""Private serializable checkpoints; never returned directly to callers."""
from pydantic import Field
from agentic_ai.schemas.food import FoodItem
from agentic_ai.schemas.nutrition import ItemSelection, NutritionItemResult, NutritionRecord, SearchResults
from agentic_ai.schemas.orchestration import Contract, SessionResponse


class ItemCheckpoint(Contract):
    item_id: str
    index: int
    effective_food: FoodItem
    selection: ItemSelection | None = None
    # Exact reply quantity takes precedence over M1's float quantity during calculation.
    quantity: str | None = None
    search: SearchResults | None = None
    records: dict[int, NutritionRecord] = Field(default_factory=dict)
    result: NutritionItemResult | None = None
    left_unresolved: bool = False


class SessionState(Contract):
    owner: str
    original_text: str
    provider: str
    response: SessionResponse
    items: list[ItemCheckpoint] = Field(default_factory=list)
    request_ids: list[str] = Field(default_factory=list)
