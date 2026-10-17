from datetime import date

from fastapi import APIRouter, Depends, Query
from pymongo.database import Database

from app.database import get_database
from app.schemas.nutrition import DailyNutritionResponse
from app.services.meals import daily_nutrition


router = APIRouter(prefix="/api/nutrition", tags=["nutrition"])


@router.get("/daily", response_model=DailyNutritionResponse)
def get_daily_nutrition(
    meal_date: date = Query(
        alias="date",
        description="Required UTC day in YYYY-MM-DD format.",
    ),
    database: Database = Depends(get_database),
) -> DailyNutritionResponse:
    return daily_nutrition(database, meal_date)
