from fastapi import APIRouter, Path

from app.api.deps import BidsUow, CurrentUserId
from app.api.schemas.bids import BidCreate, PlaceBidResponse
from app.config import settings
from app.services import bids

router = APIRouter(tags=["bids"])

# Handle bid creation requests and return the created bid, updated auction, and wallet details.
@router.post("/auctions/{id}/bids", response_model=PlaceBidResponse, status_code=201)
def create_bid(body: BidCreate, user_id: CurrentUserId, uow: BidsUow, id: int = Path(gt=0)) -> PlaceBidResponse:
    result = bids.place_bid(
        uow, user_id, id, body.amount,
        snipe_window=settings.snipe_window_seconds,
        snipe_extension=settings.snipe_extension_seconds,
    )
    return PlaceBidResponse(**result)
