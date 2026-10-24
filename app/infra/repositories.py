"""SQLAlchemy implementations of the repository ports. They convert ORM rows to plain domain entities."""

from sqlalchemy import select
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
