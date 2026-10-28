"""SQLAlchemy implementations of the repository ports. They convert ORM rows to plain domain entities."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities import User, Wallet
from app.domain.errors import UsernameTaken
from app.infra.db import models


def to_user(row: models.User) -> User:
    return User(id=row.id, username=row.username, password_hash=row.password_hash, created_at=row.created_at)


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


class SqlAlchemyAuctionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, auction: dict) -> models.Auction:
        auction = models.Auction(**auction)
        self._session.add(auction)
        self._session.flush()
        return auction

    def get(self, auction_id: int, lock: bool = False) -> models.Auction | None:
        query = select(models.Auction).where(
            models.Auction.id == auction_id,
            models.Auction.deleted_at.is_(None),
        )
        if lock:
            query = query.with_for_update()
        return self._session.scalar(query)

    def list(
        self,
        *,
        state: str,
        now,
        q: str | None,
        category: str | None,
        seller_id: int | None,
        min_price: int | None,
        max_price: int | None,
        sort: str,
        page: int,
        size: int,
    ) -> tuple[list[models.Auction], int]:
        query = select(models.Auction).where(models.Auction.deleted_at.is_(None))
        if state == "UPCOMING":
            query = query.where(
                models.Auction.status == "OPEN",
                models.Auction.start_time > now,
            )
        elif state == "FINISHED":
            query = query.where(models.Auction.end_time <= now)
        else:
            query = query.where(
                models.Auction.status == "OPEN",
                models.Auction.start_time <= now,
                models.Auction.end_time > now,
            )

        if q:
            query = query.where(models.Auction.title.ilike(f"%{q}%"))
        if category:
            query = query.where(models.Auction.category == category)
        if seller_id is not None:
            query = query.where(models.Auction.seller_id == seller_id)
        if min_price is not None:
            query = query.where(models.Auction.current_price >= min_price)
        if max_price is not None:
            query = query.where(models.Auction.current_price <= max_price)

        total = self._session.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0
        order_by = {
            "ending_soon": (models.Auction.end_time.asc(), models.Auction.id.asc()),
            "newest": (models.Auction.start_time.desc(), models.Auction.id.desc()),
            "price_asc": (models.Auction.current_price.asc(), models.Auction.id.asc()),
            "price_desc": (models.Auction.current_price.desc(), models.Auction.id.desc()),
        }[sort]
        rows = self._session.scalars(
            query.order_by(*order_by).offset((page - 1) * size).limit(size)
        ).all()
        return rows, total

    def list_for_seller(
        self,
        seller_id: int,
        status: str | None,
        page: int,
        size: int,
    ) -> tuple[list[models.Auction], int]:
        query = select(models.Auction).where(
            models.Auction.seller_id == seller_id,
            models.Auction.deleted_at.is_(None),
        )
        if status is not None:
            query = query.where(models.Auction.status == status)
        total = self._session.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0
        rows = self._session.scalars(
            query.order_by(models.Auction.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()
        return rows, total

    def delete(self, auction: models.Auction, deleted_at) -> None:
        auction.deleted_at = deleted_at
