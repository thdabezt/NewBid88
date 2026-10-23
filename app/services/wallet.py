from sqlalchemy.orm import Session

from app.domain.errors import NotFoundError
from app.infra.db.models import Wallet


def get_wallet(db: Session, user_id: int) -> Wallet:
    wallet = db.get(Wallet, user_id)
    if wallet is None:
        raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")
    return wallet


def wallet_response(wallet: Wallet) -> dict[str, int]:
    return {
        "balance": wallet.balance,
        "held": wallet.held,
        "available": wallet.balance - wallet.held,
    }
