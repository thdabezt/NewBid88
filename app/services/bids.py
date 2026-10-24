# Handles bid placement, auction updates, wallet fund holds/releases and anti-sniping extensions.

from datetime import UTC, datetime, timedelta

from app.domain.bids import validate_bid
from app.domain.errors import DomainError, NotFoundError


# Validate and place a bid, update wallet balances and auction details, and commit all changes atomically.
def place_bid(uow, user_id: int, auction_id: int, amount: int, snipe_window: int = 60, snipe_extension: int = 60) -> dict:
    with uow:
        repo = uow.bids

        # Lock the auction to prevent concurrent bid conflicts.
        auction = repo.get_auction(auction_id, lock=True)
        if auction is None:
            raise NotFoundError("AUCTION_NOT_FOUND", "Auction not found")

        now = datetime.now(UTC)
        validate_bid(auction, user_id, amount, now)

        # Preserve the previous highest bid details for releasing held funds.
        old_user_id = auction.highest_bidder_id
        old_bid_id = auction.highest_bid_id
        old_price = auction.current_price

        user_ids = [user_id]
        if old_user_id is not None:
            user_ids.append(old_user_id)

        wallets = repo.lock_wallets(user_ids)
        for wallet in wallets.values():
            if wallet is None:
                raise NotFoundError("WALLET_NOT_FOUND", "Wallet not found")

        wallet = wallets[user_id]
        available = wallet.balance - wallet.held
        if available < amount:
            raise DomainError("INSUFFICIENT_FUNDS", "Not enough available money", {"available": available})

        # Create the bid and hold the required funds without deducting the wallet balance.
        bid = repo.add_bid(auction_id, user_id, amount, now)
        wallet.held += amount
        wallet.updated_at = now
        repo.add_ledger(wallet, "BID_HOLD", amount, auction_id, bid.id, now)

        # Release the previous highest bidder's held funds.
        if old_user_id is not None:
            old_wallet = wallets[old_user_id]
            old_wallet.held -= old_price
            old_wallet.updated_at = now
            repo.add_ledger(old_wallet, "BID_RELEASE", -old_price, auction_id, old_bid_id, now)

        # Update the auction with the new highest bid.
        auction.current_price = amount
        auction.highest_bid_id = bid.id
        auction.highest_bidder_id = user_id
        auction.bid_count += 1

        # Extend the auction if the bid is placed within the anti-sniping window.
        extended = auction.end_time - now <= timedelta(seconds=snipe_window)
        if extended:
            auction.end_time = max(auction.end_time, now + timedelta(seconds=snipe_extension))
            auction.extended_count += 1

        result = {
            "bid": {
                "id": bid.id, "auction_id": auction_id,
                "amount": amount, "created_at": bid.created_at,
            },
            "auction": {
                "current_price": auction.current_price,
                "bid_count": auction.bid_count,
                "end_time": auction.end_time,
                "extended": extended,
            },
            "wallet": {
                "balance": wallet.balance,
                "held": wallet.held,
                "available": wallet.balance - wallet.held,
            },
        }

        # Commit all bid, wallet, ledger, and auction changes in a single transaction.
        uow.commit()
        return result

# Get bid history for an auction.
def bid_history(uow, auction_id: int, page: int, size: int) -> dict:
    with uow:
        uow.read_only()

        # Verify that the auction exists.
        if uow.bids.get_auction(auction_id) is None:
            raise NotFoundError("AUCTION_NOT_FOUND", "Auction not found")

        rows, total = uow.bids.history(auction_id, page, size)
        items = []

        # Mask bidder usernames by keeping only the first two characters.
        for bid, username in rows:
            items.append({
                "id": bid.id, "bidder": username[:2] + "***",
                "amount": bid.amount, "created_at": bid.created_at,
            })

        return {"items": items, "page": page, "size": size, "total": total}
