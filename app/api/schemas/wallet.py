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
