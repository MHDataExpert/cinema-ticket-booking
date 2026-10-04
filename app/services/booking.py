import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.payment import process_payment


def _ttl() -> str:
    return f"{settings.reservation_ttl_minutes} minutes"


def _availability() -> str:
    return f"(status='available' OR (status='reserved' AND reserved_at < now() - interval '{_ttl()}'))"


async def reserve_tickets(db: AsyncSession, ids: list[uuid.UUID]) -> datetime | None:
    """All-or-nothing hold for up to N seats. One atomic UPDATE; returns expiry or None."""
    q = (
        text(f"UPDATE tickets SET status='reserved', reserved_at=now() WHERE id IN :ids AND {_availability()} RETURNING id")
        .bindparams(bindparam("ids", expanding=True))
    )
    r = await db.execute(q, {"ids": list(ids)})
    rows = r.all()
    if len(rows) != len(ids):
        await db.rollback()
        return None
    await db.commit()
    return datetime.now(timezone.utc) + timedelta(minutes=settings.reservation_ttl_minutes)


async def reserve_ticket(db: AsyncSession, ticket_id: uuid.UUID) -> dict | None:
    exp = await reserve_tickets(db, [ticket_id])
    if exp is None:
        return None
    return {"ticket_id": ticket_id, "expires_at": exp}


async def confirm_tickets(db: AsyncSession, ids: list[uuid.UUID], payment_token: str):
    """Returns (code, payload). code 200/402/410/409. Persian details."""
    q = text("SELECT * FROM tickets WHERE id IN :ids").bindparams(bindparam("ids", expanding=True))
    rows = (await db.execute(q, {"ids": list(ids)})).mappings().all()
    if len(rows) != len(ids) or any(r["status"] in ("available", "booked") for r in rows):
        return 409, {"detail": "این صندلی قبلاً گرفته شده است؛ لطفاً صندلی دیگری انتخاب کنید"}
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.reservation_ttl_minutes)
    expired = []
    for r in rows:
        ra = r["reserved_at"]
        if ra is not None and ra.tzinfo is None:
            ra = ra.replace(tzinfo=timezone.utc)
        if ra is None or ra < cutoff:
            expired.append(str(r["id"]))
    if expired:
        q2 = text("UPDATE tickets SET status='available', reserved_at=NULL WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        await db.execute(q2, {"ids": [r["id"] for r in rows]})
        await db.commit()
        return 410, {"detail": "مهلت ۱۰ دقیقه‌ای رزرو تمام شد؛ صندلی آزاد شد و می‌توانید دوباره رزرو کنید"}
    if not process_payment(payment_token):
        q3 = text("UPDATE tickets SET status='available', reserved_at=NULL WHERE id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        await db.execute(q3, {"ids": [r["id"] for r in rows]})
        await db.commit()
        return 402, {"detail": "پرداخت ناموفق بود؛ صندلی آزاد شد"}
    q4 = text("UPDATE tickets SET status='booked', user_id=:u WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    await db.execute(q4, {"ids": [r["id"] for r in rows], "u": settings.demo_user_id})
    await db.commit()
    return 200, {"ticket_ids": ids, "status": "booked"}


async def confirm_ticket(db: AsyncSession, ticket_id: uuid.UUID, payment_token: str):
    code, payload = await confirm_tickets(db, [ticket_id], payment_token)
    if code == 200:
        return code, {"ticket_id": ticket_id, "status": "booked"}
    return code, payload


async def release_tickets(db: AsyncSession, ids: list[uuid.UUID]) -> None:
    q = text("UPDATE tickets SET status='available', reserved_at=NULL WHERE id IN :ids").bindparams(
        bindparam("ids", expanding=True)
    )
    await db.execute(q, {"ids": list(ids)})
    await db.commit()


async def release_ticket(db: AsyncSession, ticket_id: uuid.UUID) -> None:
    await release_tickets(db, [ticket_id])
