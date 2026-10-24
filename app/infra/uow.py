from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.infra.bids_repository import BidsRepository
from app.infra.repositories import SqlAlchemyUserRepository, SqlAlchemyWalletRepository


class SqlAlchemyUnitOfWork:
    """One session and one transaction per use case."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "SqlAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.wallets = SqlAlchemyWalletRepository(self._session)
        self.bids = BidsRepository(self._session)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # close() rolls back whatever was not committed and returns the connection to the pool.
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def read_only(self) -> None:
            self._session.execute(text("SET TRANSACTION READ ONLY"))