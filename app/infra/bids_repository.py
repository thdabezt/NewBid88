# Database operations for auction bidding, including wallet locking, bid creation, transaction logging and bid history retrieval.

from sqlalchemy import func, select
from app.infra.db.models import Auction, Bid, User, Wallet, WalletTransaction


class BidsRepository:
    def __init__(self, db):
        self.db = db

    # Retrieve an active auction and optionally lock it.
    def get_auction(self, auction_id: int, lock: bool = False):
        query = select(Auction).where(Auction.id == auction_id, Auction.deleted_at.is_(None))
        if lock:
            query = query.with_for_update()
        return self.db.execute(query).scalar_one_or_none()

    # Lock user wallets in ascending.
    def lock_wallets(self, user_ids: list[int]) -> dict:
        wallets = {}
        for user_id in sorted(set(user_ids)):
            query = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
            wallets[user_id] = self.db.execute(query).scalar_one_or_none()
        return wallets

    # Create a new bid record and flush it to obtain the generated ID without saving into the database.
    def add_bid(self, auction_id: int, user_id: int, amount: int, now):
        bid = Bid(auction_id=auction_id, bidder_id=user_id, amount=amount, created_at=now)
        self.db.add(bid)
        self.db.flush()
        return bid

    # Record wallet hold or release transactions in the ledger without saving into the database.
    def add_ledger(self, wallet, kind: str, delta: int, auction_id: int, bid_id: int, now) -> None:
        transaction = WalletTransaction(
            user_id=wallet.user_id, type=kind, balance_delta=0, held_delta=delta,
            balance_after=wallet.balance, held_after=wallet.held,
            auction_id=auction_id, bid_id=bid_id, created_at=now,
        )
        self.db.add(transaction)


    # Get bid history for an auction, ordered by newest first.
    def history(self, auction_id: int, page: int, size: int):
        total = self.db.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == auction_id))

        query = (
            select(Bid, User.username)
            .join(User, User.id == Bid.bidder_id)
            .where(Bid.auction_id == auction_id)
            .order_by(Bid.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        return self.db.execute(query).all(), total