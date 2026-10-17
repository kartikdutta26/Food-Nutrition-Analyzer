from fastapi import APIRouter

from app.schemas.nutrition import FoodAnalysisRequest, FoodAnalysisResponse
from app.services.food_analysis import analyze_food


router = APIRouter(prefix="/api/food", tags=["food"])


@router.post("/analyze", response_model=FoodAnalysisResponse)
def analyze(request: FoodAnalysisRequest) -> FoodAnalysisResponse:
    """Return a sample preset or USDA FoodData Central nutrition lookup."""

    return analyze_food(request)
