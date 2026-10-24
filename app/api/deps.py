from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.domain.errors import AuthenticationError
from app.infra.db.session import SessionLocal
from app.infra.uow import SqlAlchemyUnitOfWork
from app.services.auth_service import AuthService

# Only here so Swagger shows the lock icon and the Authorize button.
# The token itself is checked once, in JWTAuthMiddleware.
bearer_scheme = HTTPBearer(auto_error=False, description="Access token from POST /auth/login")


def get_db_ping(request: Request) -> Callable[[], bool]:
    """The database check that main.py put on app.state."""
    return request.app.state.db_ping


DbPing = Annotated[Callable[[], bool], Depends(get_db_ping)]


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


Auth = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user_id(
    request: Request,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    """The user id JWTAuthMiddleware put on request.state."""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise AuthenticationError("UNAUTHORIZED", "Authentication required")
    return user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def get_bids_uow(request: Request) -> SqlAlchemyUnitOfWork:
    return request.app.state.uow_factory()


BidsUow = Annotated[SqlAlchemyUnitOfWork, Depends(get_bids_uow)]