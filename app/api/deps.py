from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.errors import AuthenticationError
from app.infra.uow import SqlAlchemyUnitOfWork
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(
    auto_error=False, bearerFormat="JWT", description="Access token from POST /auth/login"
)


def get_db_ping(request: Request) -> Callable[[], bool]:
    return request.app.state.db_ping


DbPing = Annotated[Callable[[], bool], Depends(get_db_ping)]


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


Auth = Annotated[AuthService, Depends(get_auth_service)]


def get_current_user_id(
    request: Request,
    _credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> int:
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise AuthenticationError("UNAUTHORIZED", "Authentication required")
    return user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]


def get_uow(request: Request) -> SqlAlchemyUnitOfWork:
    return request.app.state.uow_factory()


Uow = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]