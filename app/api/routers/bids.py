from fastapi import APIRouter, Path
from fastapi import Query

from app.api.deps import BidsUow, CurrentUserId
from app.api.schemas.bids import BidHistoryResponse
from app.api.schemas.bids import MyBidsResponse, MyBidStatus
from app.api.schemas.bids import BidCreate, PlaceBidResponse

from app.config import settings
from app.services import bids

router = APIRouter(tags=["bids"])

@router.post("/auctions/{id}/bids", response_model=PlaceBidResponse, status_code=201)
def create_bid(body: BidCreate, user_id: CurrentUserId, uow: BidsUow, id: int = Path(gt=0)) -> PlaceBidResponse:
    result = bids.place_bid(
        uow, user_id, id, body.amount,
        snipe_window=settings.snipe_window_seconds,
        snipe_extension=settings.snipe_extension_seconds,
    )
    return PlaceBidResponse(**result)

@router.get("/auctions/{id}/bids", response_model=BidHistoryResponse)
def read_bid_history(uow: BidsUow, id: int = Path(gt=0), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> BidHistoryResponse:
    return BidHistoryResponse(**bids.bid_history(uow, id, page, size))

@router.get("/users/me/bids", response_model=MyBidsResponse)
def read_my_bids(user_id: CurrentUserId, uow: BidsUow, status: MyBidStatus | None = Query(None), page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100)) -> MyBidsResponse:
    return MyBidsResponse(**bids.my_bids(uow, user_id, status, page, size))