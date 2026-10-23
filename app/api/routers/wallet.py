from fastapi import APIRouter

from app.api.deps import CurrentUserId, DbSession
from app.api.schemas.wallet import TopUpRequest, TopUpResponse, WalletResponse
from app.services.wallet import get_wallet, top_up, wallet_response

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
def read_wallet(user_id: CurrentUserId, db: DbSession) -> WalletResponse:
    return WalletResponse(**wallet_response(get_wallet(db, user_id)))


@router.post("/topups", response_model=TopUpResponse, status_code=201)
def create_top_up(request: TopUpRequest, user_id: CurrentUserId, db: DbSession) -> TopUpResponse:
    transaction = top_up(db, user_id, request.amount)
    wallet = get_wallet(db, user_id)
    return TopUpResponse(
        transaction_id=transaction.id,
        amount=request.amount,
        wallet=WalletResponse(**wallet_response(wallet)),
    )
