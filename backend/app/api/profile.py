from fastapi import APIRouter, Depends
from pymongo.database import Database

from app.auth import AuthenticatedUser, get_current_user
from app.database import get_database
from app.schemas.nutrition import ProfileResponse, ProfileUpdateRequest
from app.services.profile import get_profile, update_profile


router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def read_profile(
    current_user: AuthenticatedUser = Depends(get_current_user),
    database: Database = Depends(get_database),
) -> ProfileResponse:
    return get_profile(database, current_user.user_id)


@router.patch("", response_model=ProfileResponse)
def patch_profile(
    request: ProfileUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    database: Database = Depends(get_database),
) -> ProfileResponse:
    return update_profile(database, current_user.user_id, request)
