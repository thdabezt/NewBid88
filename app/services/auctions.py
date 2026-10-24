from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.errors import DomainError, NotFoundError
from app.infra.db.models import Auction, User

AuctionPhase = Literal["LIVE", "UPCOMING", "ENDED"]
AuctionStatus = Literal["OPEN", "SOLD", "UNSOLD"]

def _get_phase(auction: Auction, now: datetime) -> AuctionPhase:
    if auction.status != "OPEN" or now >= auction.end_time:
        return "ENDED"
    if now < auction.start_time:
        return "UPCOMING"
    return "LIVE"

def _as_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise DomainError("INVALID_TIMEZONE", f"{field} must include a timezone")
    return value.astimezone(timezone.utc)

def _mask_username(username: str | None) -> str | None:
    if username is None:
        return None
    if len(username) <= 2:
        return username[0] + "*"
    return username[0] + "*" * (len(username) - 2) + username[-1]

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

def create_auction(
    db: Session,
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
    
    seller = db.get(User, seller_id)
    if seller is None:
        raise NotFoundError("USER_NOT_FOUND", "User not found")
    
    
    auction = Auction(
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
    )
    db.add(auction)
    db.commit()
    db.refresh(auction)


    return _detail(auction, seller.username, None, datetime.now(timezone.utc))

