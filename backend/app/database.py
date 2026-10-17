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
    """Create indexes used by list and daily-total queries."""

    database["meals"].create_index(
        [("meal_day", ASCENDING), ("consumed_at", ASCENDING)],
        name="meal_day_consumed_at",
    )
