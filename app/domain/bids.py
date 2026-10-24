from app.domain.errors import ConflictError, DomainError, ForbiddenError

def validate_bid(auction, user_id: int, amount: int, now) -> None:
    # Validate the bid and raise an exception if it is invalid
    if auction.status != "OPEN" or now >= auction.end_time:
        raise ConflictError("AUCTION_NOT_ACTIVE", "Auction is not active")
    
    if now < auction.start_time:
        raise ConflictError("AUCTION_NOT_STARTED", "Auction has not started")
    
    if auction.seller_id == user_id:
        raise ForbiddenError("SELLER_CANNOT_BID", "Seller cannot bid")

    if auction.highest_bidder_id == user_id:
        raise ConflictError("ALREADY_HIGHEST_BIDDER", "You are already leading")

    minimum = auction.starting_price
    
    if auction.bid_count > 0:
        minimum = auction.current_price + auction.min_increment

    if amount < minimum:
        raise DomainError("BID_TOO_LOW", "Bid is below the minimum", {"min_required": minimum})