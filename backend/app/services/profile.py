from datetime import UTC, datetime

from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.schemas.nutrition import ProfileResponse, ProfileUpdateRequest


def _profile_response(profile: dict) -> ProfileResponse:
    return ProfileResponse(
        dietary_preferences=profile.get("dietary_preferences", []),
        targets=profile.get("targets"),
        updated_at=profile.get("updated_at"),
    )


def _get_or_create_profile(database: Database, user_id: str) -> dict:
    """Create defaults atomically in user_profiles without reading legacy data."""

    try:
        return database["user_profiles"].find_one_and_update(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "dietary_preferences": [],
                    "updated_at": None,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        # Another request for this user may have won a simultaneous first read.
        profile = database["user_profiles"].find_one({"user_id": user_id})
        if profile is not None:
            return profile
        raise


def get_profile(database: Database, user_id: str) -> ProfileResponse:
    profile = _get_or_create_profile(database, user_id)
    return _profile_response(profile)


def update_profile(
    database: Database,
    user_id: str,
    request: ProfileUpdateRequest,
) -> ProfileResponse:
    changes = request.model_dump(exclude_unset=True)
    if "targets" in changes:
        changes["targets"] = request.targets.model_dump()
    if "dietary_preferences" in changes:
        unique_preferences = []
        seen = set()
        for preference in changes["dietary_preferences"]:
            normalized = preference.strip()
            key = normalized.casefold()
            if key not in seen:
                unique_preferences.append(normalized)
                seen.add(key)
        changes["dietary_preferences"] = unique_preferences

    changes["updated_at"] = datetime.now(UTC)
    insert_defaults = {"user_id": user_id}
    if "dietary_preferences" not in changes:
        insert_defaults["dietary_preferences"] = []

    update = {
        "$set": changes,
        "$setOnInsert": insert_defaults,
    }
    try:
        profile = database["user_profiles"].find_one_and_update(
            {"user_id": user_id},
            update,
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
    except DuplicateKeyError:
        # Retry against the just-created profile after a concurrent first write.
        profile = database["user_profiles"].find_one_and_update(
            {"user_id": user_id},
            update,
            upsert=False,
            return_document=ReturnDocument.AFTER,
        )
        if profile is None:
            raise
    return _profile_response(profile)
