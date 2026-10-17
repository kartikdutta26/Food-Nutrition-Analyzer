from datetime import UTC, datetime

from pymongo import ReturnDocument
from pymongo.database import Database

from app.schemas.nutrition import ProfileResponse, ProfileUpdateRequest


PROFILE_ID = "default"
DEFAULT_PROFILE = {
    "_id": PROFILE_ID,
    "dietary_preferences": [],
    "updated_at": None,
}

LEGACY_ONE_TARGETS = {"calories": 1, "protein": 1, "carbs": 1, "fats": 1}
EXPLICIT_TARGETS_FIELD = "_targets_explicitly_configured"


def _insert_defaults(changed_fields: set[str] | None = None) -> dict:
    changed_fields = changed_fields or set()
    return {
        key: value
        for key, value in DEFAULT_PROFILE.items()
        if key != "_id" and key not in changed_fields
    }


def _is_legacy_one_targets(targets: object) -> bool:
    if not isinstance(targets, dict) or set(targets) != set(LEGACY_ONE_TARGETS):
        return False
    return all(
        not isinstance(targets[key], bool) and targets[key] == expected
        for key, expected in LEGACY_ONE_TARGETS.items()
    )


def _profile_response(profile: dict) -> ProfileResponse:
    targets = profile.get("targets")
    # Earlier builds persisted the 1/1/1/1 placeholder, sometimes with an
    # updated_at timestamp. Only an explicit target save from this version
    # marks that same tuple as user-configured.
    if (
        profile.get(EXPLICIT_TARGETS_FIELD) is not True
        and _is_legacy_one_targets(targets)
    ):
        targets = None

    return ProfileResponse(
        dietary_preferences=profile.get("dietary_preferences", []),
        targets=targets,
        updated_at=profile.get("updated_at"),
    )


def get_profile(database: Database) -> ProfileResponse:
    # GET must remain a read operation. In particular, do not upsert a default
    # profile here: Atlas may grant this endpoint read access without write access.
    profile = database["profiles"].find_one({"_id": PROFILE_ID})
    return _profile_response(profile or DEFAULT_PROFILE)


def update_profile(database: Database, request: ProfileUpdateRequest) -> ProfileResponse:
    changes = request.model_dump(exclude_unset=True)
    if "targets" in changes:
        changes["targets"] = request.targets.model_dump()
        changes[EXPLICIT_TARGETS_FIELD] = True
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

    updated_at = datetime.now(UTC)
    changes["updated_at"] = updated_at
    update = {"$set": changes}
    insert_defaults = _insert_defaults(set(changes))
    if insert_defaults:
        update["$setOnInsert"] = insert_defaults
    profile = database["profiles"].find_one_and_update(
        {"_id": PROFILE_ID},
        update,
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return _profile_response(profile)
