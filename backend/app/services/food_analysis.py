from dataclasses import dataclass

from fastapi import HTTPException

from app.schemas.nutrition import FoodAnalysisRequest, FoodAnalysisResponse
from app.services.usda import lookup_usda_food


SAMPLE_DATA_NOTICE = (
    "Temporary sample nutrition values for demonstration only; "
    "not verified nutrition data or AI analysis."
)


@dataclass(frozen=True)
class FoodPreset:
    preset_id: str
    name: str
    category: str
    calories: float
    protein: float
    carbs: float
    fats: float
    fiber: float

    def response(self) -> FoodAnalysisResponse:
        return FoodAnalysisResponse(
            preset_id=self.preset_id,
            name=self.name,
            category=self.category,
            nutrition={
                "calories": self.calories,
                "protein": self.protein,
                "carbs": self.carbs,
                "fats": self.fats,
                "fiber": self.fiber,
            },
            data_source="sample_preset",
            notice=SAMPLE_DATA_NOTICE,
        )


# These values mirror the existing UI demo presets. They are kept explicitly
# separate from any future verified nutrition database or analysis provider.
SAMPLE_PRESETS = (
    FoodPreset("paneer-rice", "Paneer Rice Bowl", "Indian Vegetarian", 620, 28, 72, 22, 6),
    FoodPreset("masala-dosa", "Crispy Masala Dosa with Sambar", "South Indian", 450, 12, 68, 14, 5.5),
    FoodPreset("dal-tadka", "Yellow Dal Tadka & Brown Rice", "Home Cooked Classic", 410, 18, 64, 8, 11),
    FoodPreset("chicken-tikka-bowl", "Grilled Chicken Tikka Quinoa Bowl", "High Protein / Fitness", 540, 48, 42, 15, 7.5),
    FoodPreset("palak-paneer", "Palak Paneer with Multigrain Roti", "Nutrient Dense Green", 480, 24, 45, 20, 8),
    FoodPreset("fruit-acai-bowl", "Tropical Fruit & Greek Yogurt Platter", "Antioxidant Breakfast", 340, 16, 54, 7, 9),
)

PRESETS_BY_ID = {preset.preset_id: preset for preset in SAMPLE_PRESETS}
PRESETS_BY_NAME = {preset.name.casefold(): preset for preset in SAMPLE_PRESETS}


def analyze_food(request: FoodAnalysisRequest) -> FoodAnalysisResponse:
    preset = None
    if request.preset_id:
        preset = PRESETS_BY_ID.get(request.preset_id)
    elif request.food_name:
        if request.fdc_id is not None:
            return lookup_usda_food(request.food_name, selected_fdc_id=request.fdc_id)
        preset = PRESETS_BY_NAME.get(" ".join(request.food_name.split()).casefold())

        if preset is None:
            return lookup_usda_food(request.food_name)

    if preset is None:
        identifier = request.preset_id or request.food_name
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported food '{identifier}'. Use one of the supported presets.",
        )

    return preset.response()
