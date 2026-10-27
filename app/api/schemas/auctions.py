from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AuctionStatus = Literal["OPEN", "SOLD", "UNSOLD"]
AuctionPhase = Literal["UPCOMING", "LIVE", "ENDED"]

class CreateAuctionRequest(BaseModel):
    title: str
    description: str | None
    category: str 
    starting_price: int
    min_increment: int
    reserve_price: int | None 
    start_time: datetime | None
    end_time: datetime
    
class SellerResponse(BaseModel):
    id: int
    username: str

class AuctionSummaryResponse(BaseModel):
    id: int
    title: str
    category: str
    seller: SellerResponse
    current_price: int
    bid_count: int
    status: AuctionStatus
    phase: AuctionPhase
    start_time: datetime
    end_time: datetime


class AuctionDetailResponse(AuctionSummaryResponse):
    description: str
    starting_price: int
    min_increment: int
    highest_bidder: str | None
    has_reserve: bool
    reserve_met: bool | None
    extended_count: int
    final_price: int | None
    closed_at: datetime | None
    created_at: datetime

class AuctionListResponse(BaseModel):
    auctions: list[AuctionSummaryResponse]
    page: int
    size: int
    total: int

class MyAuctionDetail(AuctionSummaryResponse):
    starting_price: int
    min_increment: int
    reserve_price: int | None
    final_price: int | None
    winner: str | None
    closed_at: datetime | None

class MyAuctionResponse(BaseModel):
    items: list[MyAuctionDetail]
    page: int
    size: int
    total: int