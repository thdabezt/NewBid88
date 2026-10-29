"""SQLAlchemy implementations of the repository ports. They convert ORM rows to plain domain entities."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import Auction, User, Wallet, WalletTransaction
from app.domain.errors import NotFoundError, UsernameTaken
from app.infra.db import models


def to_user(row: models.User) -> User:
    return User(id=row.id, username=row.username, password_hash=row.password_hash, created_at=row.created_at)


def to_wallet(row: models.Wallet) -> Wallet:
    return Wallet(user_id=row.user_id, balance=row.balance, held=row.held, updated_at=row.updated_at)


def to_transaction(row: models.WalletTransaction) -> WalletTransaction:
    return WalletTransaction(
        id=row.id,
        user_id=row.user_id,
        type=row.type,
        balance_delta=row.balance_delta,
        held_delta=row.held_delta,
        balance_after=row.balance_after,
        held_after=row.held_after,
        auction_id=row.auction_id,
        bid_id=row.bid_id,
        created_at=row.created_at,
    )


def to_auction(row: models.Auction) -> Auction:
    return Auction(
        id=row.id,
        seller_id=row.seller_id,
        title=row.title,
        description=row.description,
        category=row.category,
        starting_price=row.starting_price,
        min_increment=row.min_increment,
        reserve_price=row.reserve_price,
        current_price=row.current_price,
        bid_count=row.bid_count,
        highest_bid_id=row.highest_bid_id,
        highest_bidder_id=row.highest_bidder_id,
        start_time=row.start_time,
        end_time=row.end_time,
        extended_count=row.extended_count,
        status=row.status,
        winner_id=row.winner_id,
        final_price=row.final_price,
        closed_at=row.closed_at,
        created_at=row.created_at,
        deleted_at=row.deleted_at,
    )


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        row = models.User(username=user.username, password_hash=user.password_hash, created_at=user.created_at)
        self._session.add(row)
        try:
            self._session.flush()
        except IntegrityError:
            # The UNIQUE constraint decides when two requests register the same username at once.
            raise UsernameTaken(user.username) from None
        return to_user(row)

    def get(self, id: int) -> User | None:
        row = self._session.get(models.User, id)
        return to_user(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        row = self._session.scalar(select(models.User).where(models.User.username == username))
        return to_user(row) if row else None

    def get_many(self, ids: list[int]) -> dict[int, User]:
        if not ids:
            return {}
        rows = self._session.scalars(select(models.User).where(models.User.id.in_(ids))).all()
        return {row.id: to_user(row) for row in rows}


class SqlAlchemyWalletRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, wallet: Wallet) -> None:
        self._session.add(
            models.Wallet(
                user_id=wallet.user_id,
                balance=wallet.balance,
                held=wallet.held,
                updated_at=wallet.updated_at,
            )
        )

    def get(self, user_id: int) -> Wallet | None:
        row = self._session.get(models.Wallet, user_id)
        return to_wallet(row) if row else None

    def credit(self, user_id: int, amount: int, now: datetime) -> tuple[WalletTransaction, Wallet]:
        row = self._session.scalar(
            select(models.Wallet).where(models.Wallet.user_id == user_id).with_for_update()
        )
        if row is None:
            raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")
        row.balance += amount
        row.updated_at = now
        transaction = models.WalletTransaction(
            user_id=user_id,
            type="TOPUP",
            balance_delta=amount,
            held_delta=0,
            balance_after=row.balance,
            held_after=row.held,
            created_at=now,
        )
        self._session.add(transaction)
        self._session.flush()
        return to_transaction(transaction), to_wallet(row)

    def list_transactions(
        self, user_id: int, transaction_type: str | None, page: int, size: int
    ) -> tuple[list[WalletTransaction], int]:
        filters = [models.WalletTransaction.user_id == user_id]
        if transaction_type is not None:
            filters.append(models.WalletTransaction.type == transaction_type)

        total = self._session.scalar(
            select(func.count()).select_from(models.WalletTransaction).where(*filters)
        ) or 0
        rows = self._session.scalars(
            select(models.WalletTransaction)
            .where(*filters)
            .order_by(models.WalletTransaction.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return [to_transaction(row) for row in rows], total

    def apply(
        self,
        user_id: int,
        transaction_type: str,
        balance_delta: int,
        held_delta: int,
        now: datetime,
        auction_id: int | None = None,
        bid_id: int | None = None,
    ) -> WalletTransaction:
        row = self._session.scalar(
            select(models.Wallet).where(models.Wallet.user_id == user_id).with_for_update()
        )
        if row is None:
            raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")
        row.balance += balance_delta
        row.held += held_delta
        row.updated_at = now
        transaction = models.WalletTransaction(
            user_id=user_id,
            type=transaction_type,
            balance_delta=balance_delta,
            held_delta=held_delta,
            balance_after=row.balance,
            held_after=row.held,
            auction_id=auction_id,
            bid_id=bid_id,
            created_at=now,
        )
        self._session.add(transaction)
        self._session.flush()
        return to_transaction(transaction)


class SqlAlchemyAuctionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, auction: Auction) -> Auction:
        row = models.Auction(
            seller_id=auction.seller_id,
            title=auction.title,
            description=auction.description,
            category=auction.category,
            starting_price=auction.starting_price,
            min_increment=auction.min_increment,
            reserve_price=auction.reserve_price,
            current_price=auction.current_price,
            bid_count=auction.bid_count,
            start_time=auction.start_time,
            end_time=auction.end_time,
            extended_count=auction.extended_count,
            status=auction.status,
            created_at=auction.created_at,
        )
        self._session.add(row)
        self._session.flush()
        return to_auction(row)

    def get(self, auction_id: int) -> Auction | None:
        row = self._session.get(models.Auction, auction_id)
        return to_auction(row) if row else None

    def lock_for_update(self, auction_id: int) -> Auction | None:
        row = self._session.scalar(
            select(models.Auction).where(models.Auction.id == auction_id).with_for_update()
        )
        return to_auction(row) if row else None

    def list_visible(self, **filters) -> tuple[list[Auction], int]:
        conditions = [models.Auction.deleted_at.is_(None)]
        if filters.get("status") is not None:
            conditions.append(models.Auction.status == filters["status"])
        if filters.get("seller_id") is not None:
            conditions.append(models.Auction.seller_id == filters["seller_id"])
        if filters.get("category"):
            conditions.append(models.Auction.category == filters["category"])
        if filters.get("title_contains"):
            conditions.append(models.Auction.title.ilike(f"%{filters['title_contains']}%"))
        if filters.get("min_price") is not None:
            conditions.append(models.Auction.current_price >= filters["min_price"])
        if filters.get("max_price") is not None:
            conditions.append(models.Auction.current_price <= filters["max_price"])
        if filters.get("starts_after") is not None:
            conditions.append(models.Auction.start_time > filters["starts_after"])
        if filters.get("starts_before") is not None:
            conditions.append(models.Auction.start_time <= filters["starts_before"])
        if filters.get("ends_after") is not None:
            conditions.append(models.Auction.end_time > filters["ends_after"])
        if filters.get("ends_before") is not None:
            conditions.append(models.Auction.end_time <= filters["ends_before"])

        query = select(models.Auction).where(*conditions)
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0

        order_by = {
            "ending_soon": (models.Auction.end_time.asc(), models.Auction.id.asc()),
            "newest": (models.Auction.start_time.desc(), models.Auction.id.desc()),
            "price_asc": (models.Auction.current_price.asc(), models.Auction.id.asc()),
            "price_desc": (models.Auction.current_price.desc(), models.Auction.id.desc()),
        }[filters.get("sort", "ending_soon")]

        rows = self._session.scalars(
            query.order_by(*order_by)
            .offset((filters.get("page", 1) - 1) * filters.get("size", 20))
            .limit(filters.get("size", 20))
        ).all()
        return [to_auction(row) for row in rows], total

    def list_for_seller(self, user_id: int, status: str | None, page: int, size: int) -> tuple[list[Auction], int]:
        conditions = [models.Auction.seller_id == user_id, models.Auction.deleted_at.is_(None)]
        if status is not None:
            conditions.append(models.Auction.status == status)

        query = select(models.Auction).where(*conditions)
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self._session.scalars(
            query.order_by(models.Auction.id.desc()).offset((page - 1) * size).limit(size)
        ).all()
        return [to_auction(row) for row in rows], total

    def mark_deleted(self, auction_id: int, now: datetime) -> None:
        row = self._session.get(models.Auction, auction_id)
        if row is not None:
            row.deleted_at = now

    def list_due_ids(self, now: datetime, limit: int) -> list[int]:
        return list(
            self._session.scalars(
                select(models.Auction.id)
                .where(
                    models.Auction.status == "OPEN",
                    models.Auction.deleted_at.is_(None),
                    models.Auction.end_time <= now,
                )
                .order_by(models.Auction.end_time, models.Auction.id)
                .limit(limit)
            )
        )

    def close(self, auction: Auction) -> None:
        row = self._session.get(models.Auction, auction.id)
        if row is not None:
            row.status = auction.status
            row.winner_id = auction.winner_id
            row.final_price = auction.final_price
            row.closed_at = auction.closed_at
