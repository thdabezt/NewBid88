from datetime import datetime

from pydantic import BaseModel


class WalletResponse(BaseModel):
    balance: int
    held: int
    available: int


class TopUpRequest(BaseModel):
    amount: int


class TopUpResponse(BaseModel):
    transaction_id: int
    amount: int
    wallet: WalletResponse


class WalletTransactionResponse(BaseModel):
    id: int
    type: str
    balance_delta: int
    held_delta: int
    balance_after: int
    held_after: int
    auction_id: int | None
    bid_id: int | None
    created_at: datetime


class WalletTransactionPage(BaseModel):
    items: list[WalletTransactionResponse]
    page: int
    size: int
    total: int
