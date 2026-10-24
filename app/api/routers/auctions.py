from typing import Literal, Annotated
from fastapi import APIRouter, Query, Response, status, Path

from app.api.deps import CurrentUserId, DbSession
from app.api.schemas.auctions import (
    CreateAuctionRequest,
    AuctionDetailResponse,
    AuctionListResponse,
)
from app.services.auctions import (
    create_auction,
    list_auctions,
    get_auction,
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

@router.get("/auctions", response_model=AuctionListResponse)
def browse_auctions(
    db: DbSession,
    state: Annotated[
        Literal["UPCOMING", "LIVE", "ENDED"],
        Query(description="Filter auctions by state"),
    ] = "LIVE",
    q: Annotated[
        str | None,
        Query(description="Search auctions by title"),
    ] = None,
    category: Annotated[
        str | None,
        Query(description="Filter auctions by category"),
    ] = None,
    seller_id: Annotated[
        int | None,
        Query(ge=1, description="Filter auctions by seller ID"),
    ] = None,
    min_price: Annotated[
        int | None,
        Query(ge=1_000, description="Filter auctions by minimum current price"),
    ] = None,
    max_price: Annotated[
        int | None,
        Query(ge=1_000, description="Filter auctions by maximum current price"),
    ] = None,
    sort_by: Annotated[
        Literal["ending_soon", "newest", "price_asc", "price_desc"],
        Query(description="Sort auctions by field"),
    ] = "ending_soon",
    page: Annotated[
        int,
        Query(ge=1, description="Page number for pagination"),
    ] = 1,
    size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of auctions per page"),
    ] = 20,
) -> AuctionListResponse:
    auctions, total = list_auctions(
        db,
        state=state,
        q=q,
        category=category,
        seller_id=seller_id,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        page=page,
        size=size,
    )
    return AuctionListResponse(
        auctions=auctions,
        page=page,
        size=size,
        total=total,
    )

@router.get("/auctions/{auction_id}", response_model=AuctionDetailResponse)
def read_auction(
    auction_id: Annotated[
        int,
        Path(ge=1),
    ],
    db: DbSession,
) -> AuctionDetailResponse:
    return AuctionDetailResponse(**get_auction(db, auction_id))