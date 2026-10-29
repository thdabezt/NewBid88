# Database operations for auction bidding, including wallet locking, bid creation, transaction logging and bid history retrieval.

from datetime import datetime

from sqlalchemy import func, select
from app.domain.entities import Auction as DomainAuction, Bid as DomainBid, Wallet as DomainWallet
from app.infra.db.models import Auction, Bid, User, Wallet
from app.infra.repositories import to_auction, to_wallet


def to_bid(row: Bid) -> DomainBid:
    return DomainBid(
        id=row.id, auction_id=row.auction_id, bidder_id=row.bidder_id,
        amount=row.amount, created_at=row.created_at,
    )


class BidsRepository:
    def __init__(self, db):
        self.db = db

    # Retrieve an active auction and optionally lock it.
    def get_auction(self, auction_id: int, lock: bool = False) -> DomainAuction | None:
        query = select(Auction).where(Auction.id == auction_id, Auction.deleted_at.is_(None))
        if lock:
            query = query.with_for_update()
        row = self.db.execute(query).scalar_one_or_none()
        return to_auction(row) if row else None

    # Lock user wallets in ascending.
    def lock_wallets(self, user_ids: list[int]) -> dict[int, DomainWallet | None]:
        wallets = {}
        for user_id in sorted(set(user_ids)):
            query = select(Wallet).where(Wallet.user_id == user_id).with_for_update()
            row = self.db.execute(query).scalar_one_or_none()
            wallets[user_id] = to_wallet(row) if row else None
        return wallets

    # Create a new bid record and flush it to obtain the generated ID without saving into the database.
    def add_bid(self, auction_id: int, user_id: int, amount: int, now: datetime) -> DomainBid:
        bid = Bid(auction_id=auction_id, bidder_id=user_id, amount=amount, created_at=now)
        self.db.add(bid)
        self.db.flush()
        return to_bid(bid)

    def update_auction(self, auction: DomainAuction) -> None:
        row = self.db.get(Auction, auction.id)
        row.current_price = auction.current_price
        row.highest_bid_id = auction.highest_bid_id
        row.highest_bidder_id = auction.highest_bidder_id
        row.bid_count = auction.bid_count
        row.end_time = auction.end_time
        row.extended_count = auction.extended_count

    # Get bid history for an auction, ordered by newest first.
    def history(self, auction_id: int, page: int, size: int) -> tuple[list[tuple[DomainBid, str]], int]:
        total = self.db.scalar(select(func.count()).select_from(Bid).where(Bid.auction_id == auction_id))

        query = (
            select(Bid, User.username)
            .join(User, User.id == Bid.bidder_id)
            .where(Bid.auction_id == auction_id)
            .order_by(Bid.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )

        rows = self.db.execute(query).all()
        return [(to_bid(bid), username) for bid, username in rows], total

    # Get all auctions the user has bid on.
    def mine(self, user_id: int, status: str | None, page: int, size: int) -> tuple[list[tuple[DomainAuction, int]], int]:
        my_bids = (
            select(Bid.auction_id, func.max(Bid.amount).label("my_highest_amount"))
            .where(Bid.bidder_id == user_id)
            .group_by(Bid.auction_id)
            .subquery()
        )

        query = (
            select(Auction, my_bids.c.my_highest_amount)
            .join(my_bids, my_bids.c.auction_id == Auction.id)
            .where(Auction.deleted_at.is_(None))
        )

        if status == "LEADING":
            query = query.where(Auction.status == "OPEN", Auction.highest_bidder_id == user_id)
        elif status == "OUTBID":
            query = query.where(Auction.status == "OPEN", Auction.highest_bidder_id != user_id)
        elif status == "WON":
            query = query.where(Auction.status == "SOLD", Auction.winner_id == user_id)
        elif status == "LOST":
            query = query.where(Auction.status == "SOLD", Auction.winner_id != user_id)
        elif status == "NO_SALE":
            query = query.where(Auction.status == "UNSOLD")

        total = self.db.scalar(select(func.count()).select_from(query.subquery()))

        query = query.order_by(Auction.end_time.desc(), Auction.id.desc()).offset((page - 1) * size).limit(size)

        rows = self.db.execute(query).all()
        return [(to_auction(auction), amount) for auction, amount in rows], total
