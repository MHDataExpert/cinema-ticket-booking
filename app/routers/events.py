import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Event

router = APIRouter()


@router.get(
    "/events/{event_id}",
    summary="جزئیات یک سانس",
    description="اطلاعات سالن، فیلم و نقشه صندلی‌های یک سانس را برمی‌گرداند.",
)
async def get_event(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    q = (
        select(Event)
        .options(selectinload(Event.venue), selectinload(Event.performer), selectinload(Event.tickets))
        .where(Event.id == event_id)
    )
    ev = (await db.execute(q)).scalar_one_or_none()
    if not ev:
        raise HTTPException(404, "سانس پیدا نشد")
    return {
        "id": ev.id,
        "name": ev.name,
        "description": ev.description,
        "event_type": ev.event_type,
        "starts_at": ev.starts_at,
        "venue": {"id": ev.venue.id, "name": ev.venue.name, "city": ev.venue.city,
                   "address": ev.venue.address, "capacity": ev.venue.capacity},
        "performer": {"id": ev.performer.id, "name": ev.performer.name,
                       "kind": ev.performer.kind, "description": ev.performer.description,
                       "director": ev.performer.director, "year": ev.performer.year},
        "tickets": [{"id": t.id, "section": t.section, "seat": t.seat,
                      "price": t.price, "status": t.status} for t in ev.tickets],
    }
