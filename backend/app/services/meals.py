from datetime import UTC, date, datetime

from bson import ObjectId
from fastapi import HTTPException
from pymongo.database import Database

from app.schemas.nutrition import (
    DailyNutritionResponse,
    MealCreateRequest,
    MealListResponse,
    MealResponse,
    NutritionValues,
)
from app.services.food_analysis import PRESETS_BY_ID


def _utc_datetime(value: datetime | None = None) -> datetime:
    result = value or datetime.now(UTC)
    if result.tzinfo is None:
        result = result.replace(tzinfo=UTC)
    return result.astimezone(UTC)


def _serialize_meal(document: dict) -> MealResponse:
    consumed_at = _utc_datetime(document["consumed_at"])
    return MealResponse(
        id=str(document["_id"]),
        preset_id=document.get("preset_id"),
        fdc_id=document.get("fdc_id"),
        name=document["name"],
        meal_slot=document["meal_slot"],
        consumed_at=consumed_at,
        meal_day=date.fromisoformat(document["meal_day"]),
        nutrition=document["nutrition"],
        data_source=document["data_source"],
        serving=document.get("serving"),
    )


def create_meal(
    database: Database,
    request: MealCreateRequest,
    user_id: str,
) -> MealResponse:
    preset_id = request.preset_id
    if preset_id:
        preset = PRESETS_BY_ID.get(preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="Unsupported food preset")
        name = preset.name
        nutrition = {
            "calories": preset.calories,
            "protein": preset.protein,
            "carbs": preset.carbs,
            "fats": preset.fats,
            "fiber": preset.fiber,
        }
        data_source = "sample_preset"
        fdc_id = None
        serving = None
    else:
        name = request.name
        nutrition = request.nutrition.model_dump()
        data_source = request.data_source
        fdc_id = request.fdc_id
        serving = request.serving.model_dump() if request.serving else None

    consumed_at = _utc_datetime(request.consumed_at)
    document = {
        "_id": ObjectId(),
        "user_id": user_id,
        "preset_id": preset_id,
        "name": name,
        "meal_slot": request.meal_slot,
        "consumed_at": consumed_at,
        "meal_day": consumed_at.date().isoformat(),
        "nutrition": nutrition,
        "data_source": data_source,
        "fdc_id": fdc_id,
        "serving": serving,
    }
    database["user_meals"].insert_one(document)
    return _serialize_meal(document)


def list_meals(
    database: Database,
    user_id: str,
    meal_day: date | None,
    limit: int,
) -> MealListResponse:
    query = {"user_id": user_id}
    if meal_day:
        query["meal_day"] = meal_day.isoformat()
    cursor = database["user_meals"].find(query).sort("consumed_at", -1).limit(limit)
    items = [_serialize_meal(document) for document in cursor]
    return MealListResponse(items=items, count=len(items))


def delete_meal(database: Database, user_id: str, meal_id: str) -> None:
    if not ObjectId.is_valid(meal_id):
        raise HTTPException(status_code=422, detail="meal_id must be a valid id")
    result = database["user_meals"].delete_one({"_id": ObjectId(meal_id), "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Meal not found")


def daily_nutrition(
    database: Database,
    user_id: str,
    meal_day: date,
) -> DailyNutritionResponse:
    documents = database["user_meals"].find({
        "user_id": user_id,
        "meal_day": meal_day.isoformat(),
    })
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fats": 0.0, "fiber": 0.0}
    meal_count = 0
    fiber_is_complete = True
    for document in documents:
        meal_count += 1
        for nutrient in totals:
            value = document["nutrition"].get(nutrient, 0)
            if nutrient == "fiber" and value is None:
                fiber_is_complete = False
            elif value is not None:
                totals[nutrient] += float(value)
    if not fiber_is_complete:
        totals["fiber"] = None
    return DailyNutritionResponse(
        date=meal_day,
        meal_count=meal_count,
        totals=NutritionValues(**totals),
    )
