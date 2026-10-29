from fastapi import APIRouter, Response

from app.api.deps import DbPing
from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database is down"}},
)
def health(db_ping: DbPing, response: Response) -> HealthResponse:
    if db_ping():
        return HealthResponse(status="ok", db="up")
    response.status_code = 503
    return HealthResponse(status="degraded", db="down")
