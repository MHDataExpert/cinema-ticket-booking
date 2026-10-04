import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base, get_db
from app.main import app
from app.models import Event, Performer, Ticket, Venue

engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=10)
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestSession() as db:
        v = Venue(id=uuid.uuid4(), name="سینما آزادی", city="تهران", address="۱ اصلی", capacity=100, seat_map={})
        v2 = Venue(id=uuid.uuid4(), name="سینما بهمن", city="مشهد", address="۲ فرعی", capacity=50, seat_map={})
        p = Performer(id=uuid.uuid4(), name="جدایی نادر از سیمین", kind="درام",
                      description="", director="اصغر فرهادی", year=2011)
        db.add_all([v, v2, p])
        await db.flush()
        e1 = Event(id=uuid.uuid4(), name="جدایی نادر از سیمین", description="",
                   event_type="درام", starts_at=datetime.now(timezone.utc) + timedelta(days=1),
                   venue_id=v.id, performer_id=p.id)
        e2 = Event(id=uuid.uuid4(), name="جدایی نادر از سیمین", description="",
                   event_type="درام", starts_at=datetime.now(timezone.utc) + timedelta(days=2),
                   venue_id=v2.id, performer_id=p.id)
        db.add_all([e1, e2])
        await db.flush()
        for i in range(5):
            db.add(Ticket(id=uuid.uuid4(), event_id=e1.id, section="regular",
                           seat=f"A-{i + 1}", price=Decimal("120000"), status="available"))
        db.add(Ticket(id=uuid.uuid4(), event_id=e2.id, section="vip",
                       seat="D-1", price=Decimal("220000"), status="available"))
        await db.commit()
        yield {"event1": e1.id, "event2": e2.id}
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    async def override():
        async with TestSession() as s:
            yield s
    app.dependency_overrides[get_db] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()
