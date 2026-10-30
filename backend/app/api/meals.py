from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status
from pymongo.database import Database

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_database
from app.schemas.nutrition import MealCreateRequest, MealListResponse, MealResponse
from app.services.meals import create_meal, delete_meal, list_meals


router = APIRouter(prefix="/api/meals", tags=["meals"])


@router.post("", response_model=MealResponse, status_code=status.HTTP_201_CREATED)
def create(
    request: MealCreateRequest,
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    database: Database = Depends(get_database),
) -> MealResponse:
    return create_meal(database, request, current_user.user_id)


@router.get("", response_model=MealListResponse)
def list_logged_meals(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    meal_date: date | None = Query(
        default=None,
        alias="date",
        description="Optional UTC day in YYYY-MM-DD format.",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum results to return (1–500).",
    ),
    database: Database = Depends(get_database),
) -> MealListResponse:
    return list_meals(database, current_user.user_id, meal_date, limit)


@router.delete("/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(
    current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    meal_id: Annotated[
        str,
        Path(
            pattern=r"^[0-9a-fA-F]{24}$",
            description="24-character hexadecimal MongoDB ID returned by POST /api/meals.",
        ),
    ],
    database: Database = Depends(get_database),
) -> Response:
    delete_meal(database, current_user.user_id, meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
