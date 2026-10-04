from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.fa import like_pattern, normalize_fa
from app.models import Event, Ticket, Venue

router = APIRouter()


@router.get(
    "/search",
    summary="جست‌وجوی فیلم‌ها",
    description="جست‌وجو بر اساس نام فیلم، شهر، ژانر و بازه تاریخ. ورودی فارسی نرمال‌سازی می‌شود (ی/ي، ک/ك، نیم‌فاصله، ارقام).",
)
async def search(
    term: str | None = None,
    city: str | None = None,
    event_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """نام پارامترها و فیلدهای خروجی انگلیسی؛ پیام‌ها فارسی."""
    limit = min(max(limit, 1), 100)
    q = select(Event).options(selectinload(Event.venue), selectinload(Event.performer)).join(Event.venue)
    if term:
        like = like_pattern(term)
        q = q.where((Event.name.ilike(like)) | (Event.description.ilike(like)))
    if city:
        q = q.where(Venue.city == normalize_fa(city))
    if event_type:
        q = q.where(Event.event_type == event_type)
    if date_from:
        q = q.where(Event.starts_at >= date_from)
    if date_to:
        q = q.where(Event.starts_at <= date_to)
    q = q.order_by(Event.starts_at).limit(limit).offset(offset)
    events = (await db.execute(q)).scalars().all()
    mins = dict((await db.execute(
        select(Ticket.event_id, func.min(Ticket.price))
        .where(Ticket.event_id.in_([e.id for e in events]))
        .group_by(Ticket.event_id))).all()) if events else {}
    return [{
        "id": ev.id, "name": ev.name, "event_type": ev.event_type,
        "starts_at": ev.starts_at, "venue_name": ev.venue.name,
        "city": ev.venue.city, "performer_name": ev.performer.name,
        "min_price": mins.get(ev.id),
    } for ev in events]
