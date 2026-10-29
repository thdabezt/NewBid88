from fastapi import APIRouter

from app.api.deps import Auth
from app.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.api.schemas.errors import ErrorResponse
from app.api.schemas.users import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=201,
    response_model=UserResponse,
    responses={409: {"model": ErrorResponse, "description": "USERNAME_TAKEN"}},
)
def register(body: RegisterRequest, auth: Auth) -> UserResponse:
    user = auth.register(body.username, body.password)
    return UserResponse(id=user.id, username=user.username, created_at=user.created_at)


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse, "description": "INVALID_CREDENTIALS"}},
)
def login(body: LoginRequest, auth: Auth) -> TokenResponse:
    token, expires_in = auth.login(body.username, body.password)
    return TokenResponse(access_token=token, expires_in=expires_in)
