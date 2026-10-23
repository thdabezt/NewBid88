from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.errors import DomainError, NotFoundError
from app.infra.db.models import Wallet, WalletTransaction

MIN_TOP_UP = 10_000
MAX_TOP_UP = 50_000_000


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


def top_up(db: Session, user_id: int, amount: int) -> WalletTransaction:
    if not MIN_TOP_UP <= amount <= MAX_TOP_UP:
        raise DomainError(
            "INVALID_AMOUNT",
            "Top-up amount must be between 10000 and 50000000",
        )

    wallet = db.execute(
        select(Wallet).where(Wallet.user_id == user_id).with_for_update()
    ).scalar_one_or_none()
    if wallet is None:
        raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")

    wallet.balance += amount
    transaction = WalletTransaction(
        user_id=user_id,
        type="TOPUP",
        balance_delta=amount,
        held_delta=0,
        balance_after=wallet.balance,
        held_after=wallet.held,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    user_id: int,
    transaction_type: str | None,
    page: int,
    size: int,
) -> tuple[list[WalletTransaction], int]:
    filters = [WalletTransaction.user_id == user_id]
    if transaction_type is not None:
        filters.append(WalletTransaction.type == transaction_type)

    total = db.scalar(select(func.count()).select_from(WalletTransaction).where(*filters)) or 0
    items = db.scalars(
        select(WalletTransaction)
        .where(*filters)
        .order_by(WalletTransaction.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return items, total
