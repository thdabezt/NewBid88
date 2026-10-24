from datetime import datetime

from pydantic import BaseModel, Field

from app.api.schemas.wallet import WalletResponse

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