from datetime import datetime, timezone

from app.domain.entities import Wallet, WalletTransaction
from app.domain.errors import DomainError, NotFoundError

MIN_TOP_UP = 10_000
MAX_TOP_UP = 50_000_000


def get_wallet(uow, user_id: int) -> Wallet:
    with uow:
        uow.read_only()
        wallet = uow.wallets.get(user_id)
        if wallet is None:
            raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")
        return wallet


def wallet_response(wallet: Wallet) -> dict[str, int]:
    return {
        "balance": wallet.balance,
        "held": wallet.held,
        "available": wallet.balance - wallet.held,
    }


def top_up(uow, user_id: int, amount: int) -> tuple[WalletTransaction, Wallet]:
    if not MIN_TOP_UP <= amount <= MAX_TOP_UP:
        raise DomainError(
            "INVALID_AMOUNT",
            "Top-up amount must be between 10000 and 50000000",
        )

    with uow:
        transaction, wallet = uow.wallets.credit(user_id, amount, datetime.now(timezone.utc))
        uow.commit()
        return transaction, wallet


def list_transactions(
    uow,
    user_id: int,
    transaction_type: str | None,
    page: int,
    size: int,
) -> tuple[list[WalletTransaction], int]:
    with uow:
        uow.read_only()
        return uow.wallets.list_transactions(user_id, transaction_type, page, size)
