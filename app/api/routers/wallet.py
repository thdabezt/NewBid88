from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession
from app.api.schemas.wallet import WalletResponse
from app.services.wallet import get_wallet, wallet_response

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
def read_wallet(user_id: CurrentUserId, db: DbSession) -> WalletResponse:
    return WalletResponse(**wallet_response(get_wallet(db, user_id)))
