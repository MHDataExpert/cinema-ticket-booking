import asyncio

from sqlalchemy import text

from app.config import settings
from app.db import SessionLocal


async def sweep_expired() -> int:
    async with SessionLocal() as db:
        r = await db.execute(
            text(
                "UPDATE tickets SET status='available', reserved_at=NULL "
                f"WHERE status='reserved' AND reserved_at < now() - interval '{settings.reservation_ttl_minutes} minutes'"
            )
        )
        await db.commit()
        return r.rowcount


async def sweeper_loop() -> None:
    while True:
        await asyncio.sleep(settings.sweep_interval_seconds)
        try:
            await sweep_expired()
        except Exception:
            pass
