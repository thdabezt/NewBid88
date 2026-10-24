from functools import partial

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import JWTAuthMiddleware
from app.api.routers import auctions, auth, health, users, wallet, bids
from app.config import settings
from app.infra.clock import SystemClock
from app.infra.db.session import SessionLocal, ping
from app.infra.security import BcryptHasher, JwtTokenService
from app.infra.uow import SqlAlchemyUnitOfWork
from app.services.auth_service import AuthService

# Composition root: the only place that wires api, services and infra together.
clock = SystemClock()
tokens = JwtTokenService(settings.jwt_secret, settings.jwt_expire_minutes, clock)
uow_factory = partial(SqlAlchemyUnitOfWork, SessionLocal)

app = FastAPI(title="NewBid88 API")
app.state.db_ping = ping
app.state.uow_factory = uow_factory
app.state.auth_service = AuthService(uow_factory, BcryptHasher(settings.bcrypt_rounds), tokens, clock)

app.add_middleware(JWTAuthMiddleware, tokens=tokens)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(wallet.router)
app.include_router(auctions.router)
app.include_router(bids.router)

register_error_handlers(app)