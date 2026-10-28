from datetime import datetime, timedelta, timezone
from typing import Literal

from app.config import settings
from app.domain.entities import Auction
from app.domain.errors import ConflictError, DomainError, ForbiddenError, NotFoundError, ValidationError

AuctionPhase = Literal["LIVE", "UPCOMING", "FINISHED"]
AuctionStatus = Literal["OPEN", "SOLD", "UNSOLD"]

def _get_phase(auction: Auction, now: datetime) -> AuctionPhase:
    if auction.status != "OPEN" or now >= auction.end_time:
        return "FINISHED"
    if now < auction.start_time:
        return "UPCOMING"
    return "LIVE"

def _as_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise DomainError("INVALID_TIME_RANGE", f"{field} must include a timezone")
    return value.astimezone(timezone.utc)

def _mask_username(username: str | None) -> str | None:
    if username is None:
        return None
    return username[:2] + "***"

def _detail(auction: Auction, seller_username: str, leader_username: str | None, now: datetime) -> dict:
    response = _summary(auction, seller_username, now)
    response.update(
        {
            "starting_price": auction.starting_price,
            "min_increment": auction.min_increment,
            "highest_bidder": _mask_username(leader_username),
            "has_reserve": auction.reserve_price is not None,
            "reserve_met": (
                None
                if auction.reserve_price is None
                else auction.current_price >= auction.reserve_price
            ),
            "extended_count": auction.extended_count,
            "final_price": auction.final_price,
            "closed_at": auction.closed_at,
            "created_at": auction.created_at,
        }
    )
    return response

def _summary(auction: Auction, seller_username: str, now: datetime) -> dict:
    return {
        "id": auction.id,
        "title": auction.title,
        "description": auction.description,
        "category": auction.category,
        "seller": {"id": auction.seller_id, "username": seller_username},
        "current_price": auction.current_price,
        "bid_count": auction.bid_count,
        "status": auction.status,
        "phase": _get_phase(auction, now),
        "start_time": auction.start_time,
        "end_time": auction.end_time,
    }

def _my_auction_detail(auction: Auction, seller_username: str, winner_username: str | None) -> dict:
    response = _summary(auction, seller_username, datetime.now(timezone.utc))
    response.update(
        {
            "starting_price": auction.starting_price,
            "min_increment": auction.min_increment,
            "reserve_price": auction.reserve_price,
            "final_price": auction.final_price,
            "winner": _mask_username(winner_username),
            "closed_at": auction.closed_at,
        }
    )
    return response

def create_auction(
    uow,
    seller_id: int,
    *,
    title: str,
    description: str | None,
    category: str,
    starting_price: int,
    min_increment: int,
    reserve_price: int | None,
    start_time: datetime | None,
    end_time: datetime,
) -> dict:
    if starting_price < 1_000 or min_increment < 1_000:
        raise DomainError("INVALID_PRICE", "Starting price and minimum increment must be at least 1000")
    if reserve_price is not None and reserve_price < starting_price:
        raise DomainError("INVALID_PRICE", "Reserve price cannot be below starting price")

    now = datetime.now(timezone.utc)
    starts = _as_utc(start_time or now, "start_time")
    ends = _as_utc(end_time, "end_time")
    duration = ends - starts
    min_duration = timedelta(seconds=settings.min_auction_seconds)
    max_duration = timedelta(days=settings.max_auction_days)

    latest_start = now + max_duration
    earliest_start = now - timedelta(seconds=5)
    if (
        starts < earliest_start
        or starts > latest_start
        or duration < min_duration
        or duration > max_duration
    ):
        raise DomainError("INVALID_TIME_RANGE", "Auction times are outside the allowed range")

    with uow:
        seller = uow.users.get(seller_id)
        if seller is None:
            raise NotFoundError("USER_NOT_FOUND", "User not found")

        auction = uow.auctions.add(
            Auction(
                seller_id=seller_id,
                title=title,
                description=description or "",
                category=category,
                starting_price=starting_price,
                min_increment=min_increment,
                reserve_price=reserve_price,
                current_price=starting_price,
                bid_count=0,
                start_time=starts,
                end_time=ends,
                extended_count=0,
                status="OPEN",
                created_at=now,
            )
        )
        uow.commit()
        return _detail(auction, seller.username, None, datetime.now(timezone.utc))

def list_auctions(
    uow,
    *,
    state: AuctionPhase = "LIVE",
    q: str | None = None,
    category: str | None = None,
    seller_id: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    sort: Literal["ending_soon", "newest", "price_asc", "price_desc"] = "ending_soon",
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    if page < 1:
        raise ValidationError("INVALID_PAGE", "Page must be at least 1")
    if size < 1 or size > 100:
        raise ValidationError("INVALID_PAGE_SIZE", "Page size must be between 1 and 100")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationError("INVALID_PRICE_RANGE", "Minimum price cannot exceed maximum price")
    if sort not in ("ending_soon", "newest", "price_asc", "price_desc"):
        raise ValidationError("INVALID_SORT", "Unsupported auction sort order")

    now = datetime.now(timezone.utc)
    if state == "UPCOMING":
        filters = {"status": "OPEN", "starts_after": now}
    elif state == "FINISHED":
        filters = {"ends_before": now}
    else:
        filters = {"status": "OPEN", "starts_before": now, "ends_after": now}

    with uow:
        uow.read_only()
        auctions, total = uow.auctions.list_visible(
            title_contains=q,
            category=category,
            seller_id=seller_id,
            min_price=min_price,
            max_price=max_price,
            sort=sort,
            page=page,
            size=size,
            **filters,
        )
        seller_ids = {auction.seller_id for auction in auctions}
        seller_map = {uid: user.username for uid, user in uow.users.get_many(list(seller_ids)).items()}

        return [
            _summary(auction, seller_map.get(auction.seller_id, ""), now) for auction in auctions
        ], total

def get_auction(uow, auction_id: int) -> dict:
    with uow:
        uow.read_only()
        auction = uow.auctions.get(auction_id)
        if not auction or auction.deleted_at is not None:
            raise NotFoundError("AUCTION_NOT_FOUND", "Auction not found")

        seller = uow.users.get(auction.seller_id)
        if not seller:
            raise NotFoundError("AUCTION_NOT_FOUND", "Seller not found")

        leader_username = None
        if auction.highest_bidder_id:
            leader = uow.users.get(auction.highest_bidder_id)
            leader_username = leader.username if leader else None

        return _detail(auction, seller.username, leader_username, datetime.now(timezone.utc))

def delete_auction(uow, auction_id: int, user_id: int) -> None:
    with uow:
        auction = uow.auctions.lock_for_update(auction_id)
        if not auction or auction.deleted_at is not None:
            raise NotFoundError("AUCTION_NOT_FOUND", "Auction not found")
        if auction.seller_id != user_id:
            raise ForbiddenError("NOT_OWNER", "You are not the owner of this auction")
        if auction.bid_count > 0:
            raise ConflictError("AUCTION_HAS_BIDS", "Cannot delete an auction that has bids")
        now = datetime.now(timezone.utc)
        if auction.status != "OPEN" or now >= auction.end_time:
            raise ConflictError("AUCTION_NOT_CANCELLABLE", "Only open auctions can be deleted")

        uow.auctions.mark_deleted(auction_id, now)
        uow.commit()

def get_my_auctions(
    uow,
    user_id: int,
    *,
    status: AuctionStatus | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    if page < 1:
        raise ValidationError("INVALID_PAGE", "Page must be at least 1")
    if size < 1 or size > 100:
        raise ValidationError("INVALID_PAGE_SIZE", "Page size must be between 1 and 100")

    with uow:
        uow.read_only()
        seller = uow.users.get(user_id)
        if seller is None:
            raise NotFoundError("USER_NOT_FOUND", "User not found")

        auctions, total = uow.auctions.list_for_seller(user_id, status, page, size)
        winner_ids = [
            auction.winner_id for auction in auctions if auction.winner_id is not None
        ]
        winner_map = {uid: user.username for uid, user in uow.users.get_many(winner_ids).items()}

        return [
            _my_auction_detail(
                auction,
                seller.username,
                winner_map.get(auction.winner_id),
            )
            for auction in auctions
        ], total
