from typing import Any

from fastapi import Request
from pymongo import ASCENDING
from pymongo.database import Database


def get_database(request: Request) -> Database[Any]:
    """FastAPI dependency for the database attached during application startup."""

    database = getattr(request.app.state, "database", None)
    if database is None:
        raise RuntimeError("MongoDB database is not initialized")
    return database


def initialize_database(database: Database[Any]) -> None:
    """Create indexes only for the new user-owned collections."""

    database["user_profiles"].create_index(
        [("user_id", ASCENDING)],
        unique=True,
        name="user_profiles_user_id_unique",
    )
    database["user_meals"].create_index(
        [("user_id", ASCENDING), ("meal_day", ASCENDING), ("consumed_at", -1)],
        name="user_meals_user_day_consumed_at",
    )
    database["user_meals"].create_index(
        [("user_id", ASCENDING), ("consumed_at", -1)],
        name="user_meals_user_consumed_at",
    )
