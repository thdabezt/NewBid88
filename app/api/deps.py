from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.domain.errors import AuthenticationError
from app.infra.db.session import SessionLocal
from app.services.auth_service import AuthService


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


def get_current_user_id(request: Request) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise AuthenticationError("UNAUTHORIZED", "Authentication required")
    return user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
