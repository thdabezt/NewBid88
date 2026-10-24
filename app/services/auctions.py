from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.config import settings
from app.domain.errors import DomainError, NotFoundError, ValidationError
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

def list_auctions(
    db: Session,
    *,
    state: AuctionPhase = "LIVE",
    q: str | None = None,
    category: str | None = None,
    seller_id: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    sort_by: Literal["ending_soon", "newest", "price_asc", "price_desc"] = "ending_soon",
    page: int = 1,
    size: int = 20,
) -> tuple[list[dict], int]:
    if page < 1:
        raise ValidationError("INVALID_PAGE", "Page must be at least 1")
    if size < 1 or size > 100:
        raise ValidationError("INVALID_PAGE_SIZE", "Page size must be between 1 and 100")
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationError("INVALID_PRICE_RANGE", "Minimum price cannot exceed maximum price")

    now = datetime.now(timezone.utc)
    query = db.query(Auction).filter(Auction.deleted_at.is_(None))

    if state == "UPCOMING":
        query = query.filter(Auction.start_time > now)
    elif state == "ENDED":
        query = query.filter(Auction.end_time <= now)
    else:
        query = query.filter(Auction.start_time <= now, Auction.end_time > now)

    if q:
        query = query.filter(Auction.title.ilike(f"%{q}%"))
    if category:
        query = query.filter(Auction.category == category)
    if seller_id is not None:
        query = query.filter(Auction.seller_id == seller_id)
    if min_price is not None:
        query = query.filter(Auction.current_price >= min_price)
    if max_price is not None:
        query = query.filter(Auction.current_price <= max_price)

    total = query.count()

    if sort_by == "ending_soon":
        ordered_query = query.order_by(Auction.end_time.asc(), Auction.id.asc())
    elif sort_by == "newest":
        ordered_query = query.order_by(Auction.start_time.desc(), Auction.id.desc())
    elif sort_by == "price_asc":
        ordered_query = query.order_by(Auction.current_price.asc(), Auction.id.asc())
    elif sort_by == "price_desc":
        ordered_query = query.order_by(Auction.current_price.desc(), Auction.id.desc())
    else:
        raise ValidationError("INVALID_SORT", "Unsupported auction sort order")

    auctions = ordered_query.offset((page - 1) * size).limit(size).all()
    seller_ids = {auction.seller_id for auction in auctions}
    sellers = db.query(User).filter(User.id.in_(seller_ids)).all() if seller_ids else []
    seller_map = {seller.id: seller.username for seller in sellers}

    return [
        _summary(auction, seller_map.get(auction.seller_id, ""), now) for auction in auctions
    ], total