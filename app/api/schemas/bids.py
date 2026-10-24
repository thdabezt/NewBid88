from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.wallet import WalletResponse

from typing import Literal

class BidCreate(BaseModel):
    amount: int = Field(strict=True)

class BidInfo(BaseModel):
    id: int                    
    auction_id: int           
    amount: int              
    created_at: datetime        
    
class BidAuctionInfo(BaseModel):
    current_price: int            
    bid_count: int                
    end_time: datetime          
    extended: bool                

class PlaceBidResponse(BaseModel):
    bid: BidInfo
    auction: BidAuctionInfo
    wallet: WalletResponse


class BidHistoryItem(BaseModel):
    id: int
    bidder: str
    amount: int
    created_at: datetime


class BidHistoryResponse(BaseModel):
    items: list[BidHistoryItem]
    page: int    
    size: int   
    total: int 

MyBidStatus = Literal["LEADING", "OUTBID", "WON", "LOST", "NO_SALE"]

class MyBidAuction(BaseModel):
    id: int
    title: str
    status: Literal["OPEN", "SOLD", "UNSOLD"]
    phase: Literal["UPCOMING", "LIVE", "FINISHED"]
    current_price: int
    end_time: datetime

class MyBidItem(BaseModel):
    auction: MyBidAuction
    my_highest_amount: int
    my_status: MyBidStatus

class MyBidsResponse(BaseModel):
    items: list[MyBidItem]
    page: int
    size: int
    total: int