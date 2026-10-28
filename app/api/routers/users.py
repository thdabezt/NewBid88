from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import Auth, BidsUow, CurrentUserId
from app.api.schemas.errors import ErrorResponse
from app.api.schemas.users import UserResponse

from app.api.schemas.auctions import MyAuctionResponse
from app.services.auctions import get_my_auctions

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


@router.get("/me/auctions", response_model=MyAuctionResponse)
def fetch_my_auctions(
    user_id: CurrentUserId,
    uow: BidsUow,
    auction_status: Annotated[
        Literal["OPEN", "SOLD", "UNSOLD"] | None,
        Query(alias="status"),
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number for pagination"),
    ] = 1,
    size: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 20,
) -> MyAuctionResponse:
    auctions, total = get_my_auctions(uow, user_id, status=auction_status, page=page, size=size)
    return MyAuctionResponse(items=auctions, page=page, size=size, total=total)
