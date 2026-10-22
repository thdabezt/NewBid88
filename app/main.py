from fastapi import FastAPI

from app.api.errors import register_error_handlers

app = FastAPI(title="NewBid88 API")
register_error_handlers(app)
