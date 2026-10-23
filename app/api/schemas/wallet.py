from pydantic import BaseModel


class WalletResponse(BaseModel):
    balance: int
    held: int
    available: int
