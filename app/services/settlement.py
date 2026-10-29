from dataclasses import replace

from app.domain.ports import Clock, UnitOfWorkFactory


class SettlementService:
    def __init__(self, uow: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def due(self, limit: int) -> list[int]:
        with self._uow() as uow:
            uow.read_only()
            return uow.auctions.list_due_ids(self._clock.now(), limit)

    def settle(self, auction_id: int) -> str | None:
        with self._uow() as uow:
            auction = uow.auctions.lock_for_update(auction_id)
            now = self._clock.now()
            if auction is None or auction.deleted_at is not None or auction.status != "OPEN" or now < auction.end_time:
                return None

            leader_id = auction.highest_bidder_id
            price = auction.current_price
            sold = leader_id is not None and (auction.reserve_price is None or price >= auction.reserve_price)

            if sold:
                moves = {
                    leader_id: ("SETTLEMENT_PAY", -price, -price),
                    auction.seller_id: ("SETTLEMENT_RECEIVE", price, 0),
                }
                for user_id in sorted(moves):
                    transaction_type, balance_delta, held_delta = moves[user_id]
                    uow.wallets.apply(
                        user_id, transaction_type, balance_delta, held_delta, now, auction.id, auction.highest_bid_id
                    )
                closed = replace(auction, status="SOLD", winner_id=leader_id, final_price=price, closed_at=now)
            else:
                if leader_id is not None:
                    uow.wallets.apply(leader_id, "BID_RELEASE", 0, -price, now, auction.id, auction.highest_bid_id)
                closed = replace(auction, status="UNSOLD", closed_at=now)

            uow.auctions.close(closed)
            uow.commit()
            return closed.status
