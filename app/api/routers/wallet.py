from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUserId, Uow
from app.api.schemas.wallet import (
    TopUpRequest,
    TopUpResponse,
    WalletResponse,
    WalletTransactionPage,
    WalletTransactionResponse,
)
from app.services.wallet import get_wallet, list_transactions, top_up, wallet_response

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletResponse)
def read_wallet(user_id: CurrentUserId, uow: Uow) -> WalletResponse:
    return WalletResponse(**wallet_response(get_wallet(uow, user_id)))


@router.post("/topups", response_model=TopUpResponse, status_code=201)
def create_top_up(request: TopUpRequest, user_id: CurrentUserId, uow: Uow) -> TopUpResponse:
    transaction, wallet = top_up(uow, user_id, request.amount)
    return TopUpResponse(
        transaction_id=transaction.id,
        amount=request.amount,
        wallet=WalletResponse(**wallet_response(wallet)),
    )


@router.get("/transactions", response_model=WalletTransactionPage)
def read_transactions(
    user_id: CurrentUserId,
    uow: Uow,
    transaction_type: Annotated[
        Literal["TOPUP", "BID_HOLD", "BID_RELEASE", "SETTLEMENT_PAY", "SETTLEMENT_RECEIVE"] | None,
        Query(alias="type"),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> WalletTransactionPage:
    items, total = list_transactions(uow, user_id, transaction_type, page, size)
    return WalletTransactionPage(
        items=[WalletTransactionResponse.model_validate(item, from_attributes=True) for item in items],
        page=page,
        size=size,
        total=total,
    )
