from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUserId, DbSession
from app.api.schemas.auctions import (
    CreateAuctionRequest,
    AuctionDetailResponse,
)
from app.services.auctions import (
    create_auction,
)

router = APIRouter(tags=["auctions"])

@router.post("/auctions", response_model=AuctionDetailResponse, status_code=status.HTTP_201_CREATED)
def create_auction_endpoint(
    request: CreateAuctionRequest,
    response: Response,
    user_id: CurrentUserId,
    db: DbSession,
) -> AuctionDetailResponse:
    auction = create_auction(
        db,
        user_id,
        title=request.title,
        description=request.description,
        category=request.category,
        starting_price=request.starting_price,
        min_increment=request.min_increment,
        reserve_price=request.reserve_price,
        start_time=request.start_time,
        end_time=request.end_time,
    )
    response.headers["Location"] = f"/auctions/{auction['id']}"
    return AuctionDetailResponse(**auction)

