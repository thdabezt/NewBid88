from fastapi import APIRouter

from app.api.deps import Auth, CurrentUserId
from app.api.schemas.errors import ErrorResponse
from app.api.schemas.users import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        401: {"model": ErrorResponse, "description": "UNAUTHORIZED"},
        404: {"model": ErrorResponse, "description": "USER_NOT_FOUND"},
    },
)
def me(user_id: CurrentUserId, auth: Auth) -> UserResponse:
    """The logged-in user's account."""
    user = auth.get_user(user_id)
    return UserResponse(id=user.id, username=user.username, created_at=user.created_at)
