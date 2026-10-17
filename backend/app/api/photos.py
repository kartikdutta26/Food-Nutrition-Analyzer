from typing import Annotated

from fastapi import APIRouter, Query

from app.schemas.photos import FoodPhotoResponse
from app.services.unsplash import search_food_photo


router = APIRouter(prefix="/api/food", tags=["food photos"])


@router.get("/photo", response_model=FoodPhotoResponse)
def food_photo(
    food_name: Annotated[str, Query(min_length=1, max_length=120)],
) -> FoodPhotoResponse:
    """Find an attributed Unsplash photograph for a selected food."""

    return search_food_photo(food_name)
