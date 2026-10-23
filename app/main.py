from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routers import health, wallet
from app.infra.db.session import ping

# Composition root: the only place that wires api, services and infra together.
app = FastAPI(title="NewBid88 API")
app.state.db_ping = ping

app.include_router(health.router)
app.include_router(wallet.router)
register_error_handlers(app)
