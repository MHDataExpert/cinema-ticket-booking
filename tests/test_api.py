import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.config import settings
from app.fa import normalize_fa
from app.models import Ticket
from tests.conftest import TestSession

pytestmark = pytest.mark.asyncio


async def _seat_ids(event_id, n=1, section=None):
    async with TestSession() as db:
        q = select(Ticket).where(Ticket.event_id == event_id, Ticket.status == "available")
        if section:
            q = q.where(Ticket.section == section)
        q = q.limit(n)
        rows = (await db.execute(q)).scalars().all()
        return [t.id for t in rows]


async def test_event_detail_nesting(client, setup_db):
    r = await client.get(f"/events/{setup_db['event1']}")
    assert r.status_code == 200
    body = r.json()
    assert body["venue"]["name"] == "سینما آزادی"
    assert body["performer"]["name"] == "جدایی نادر از سیمین"
    assert body["performer"]["director"] == "اصغر فرهادی"
    assert len(body["tickets"]) == 5
    assert set(body["tickets"][0]) == {"id", "section", "seat", "price", "status"}
    r = await client.get(f"/events/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_reserve_success(client, setup_db):
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    r = await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    assert r.status_code == 200
    assert r.json()["status"] == "reserved"
    await client.post("/bookings/release", json={"ticket_id": str(tid)})


async def test_multi_reserve_all_or_nothing(client, setup_db):
    ids = [str(i) for i in await _seat_ids(setup_db["event1"], 2)]
    r = await client.post("/bookings/reserve", json={"ticket_ids": ids})
    assert r.status_code == 200
    # stealing one of them must fail the whole batch
    r2 = await client.post("/bookings/reserve", json={"ticket_ids": ids})
    assert r2.status_code == 409
    await client.post("/bookings/release", json={"ticket_ids": ids})


async def test_multi_limit_6(client, setup_db):
    r = await client.post("/bookings/reserve", json={"ticket_ids": [str(uuid.uuid4()) for _ in range(7)]})
    assert r.status_code == 422


async def test_double_reserve_conflict(client, setup_db):
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    results = await asyncio.gather(*[
        client.post("/bookings/reserve", json={"ticket_id": str(tid)}) for _ in range(5)
    ])
    assert sum(r.status_code == 200 for r in results) == 1
    assert sum(r.status_code == 409 for r in results) == 4
    await client.post("/bookings/release", json={"ticket_id": str(tid)})


async def test_expired_reservable(client, setup_db):
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    async with TestSession() as db:
        await db.execute(text("UPDATE tickets SET reserved_at = now() - interval '15 minutes' WHERE id=:id"),
                         {"id": tid})
        await db.commit()
    r = await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    assert r.status_code == 200
    await client.post("/bookings/release", json={"ticket_id": str(tid)})


async def test_confirm_happy_path(client, setup_db):
    tid = (await _seat_ids(setup_db["event2"], 1))[0]
    await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    r = await client.put("/bookings/confirm", json={"ticket_id": str(tid), "payment_token": "tok_ok"})
    assert r.status_code == 200
    assert r.json()["status"] == "booked"
    async with TestSession() as db:
        t = (await db.execute(select(Ticket).where(Ticket.id == tid))).scalar_one()
        assert t.user_id == settings.demo_user_id
        t.status = "available"; t.reserved_at = None; t.user_id = None
        await db.commit()


async def test_confirm_expired_410(client, setup_db):
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    async with TestSession() as db:
        await db.execute(text("UPDATE tickets SET reserved_at = now() - interval '15 minutes' WHERE id=:id"),
                         {"id": tid})
        await db.commit()
    r = await client.put("/bookings/confirm", json={"ticket_id": str(tid), "payment_token": "tok_ok"})
    assert r.status_code == 410
    assert "۱۰ دقیقه" in r.json()["detail"]


async def test_confirm_payment_fail_402_releases(client, setup_db):
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    r = await client.put("/bookings/confirm", json={"ticket_id": str(tid), "payment_token": "fail"})
    assert r.status_code == 402
    async with TestSession() as db:
        t = (await db.execute(select(Ticket).where(Ticket.id == tid))).scalar_one()
        assert t.status == "available"


async def test_search_filters(client, setup_db):
    r = await client.get("/search", params={"term": "جدایی"})
    assert r.status_code == 200 and any("جدایی" in e["name"] for e in r.json())
    r = await client.get("/search", params={"city": "مشهد"})
    assert all(e["city"] == "مشهد" for e in r.json()) and len(r.json()) == 1
    r = await client.get("/search", params={"event_type": "درام"})
    assert all(e["event_type"] == "درام" for e in r.json())
    r = await client.get("/search", params={"date_from": "2030-01-01T00:00:00Z"})
    assert r.json() == []
    r = await client.get("/search", params={"limit": 1, "offset": 0})
    assert len(r.json()) == 1
    body = r.json()[0]
    assert set(body) == {"id", "name", "event_type", "starts_at", "venue_name", "city", "performer_name", "min_price"}


async def test_search_fa_normalization(client, setup_db):
    # arabic ي + half-space vs persian form must both match بچه‌های-style titles
    r = await client.get("/search", params={"term": "جدايي نادر از سيمين"})
    assert r.status_code == 200 and any("جدایی" in e["name"] for e in r.json())
    r = await client.get("/search", params={"term": "جدایی‌نادر‌از‌سیمین"})
    assert r.status_code == 200 and any("جدایی" in e["name"] for e in r.json())
    assert normalize_fa("بچه‌های سيمين") == normalize_fa("بچه هاي سیمین")


async def test_sweeper_releases_expired(client, setup_db):
    from app.tasks import sweep_expired
    tid = (await _seat_ids(setup_db["event1"], 1))[0]
    await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    async with TestSession() as db:
        await db.execute(text("UPDATE tickets SET reserved_at = now() - interval '15 minutes' WHERE id=:id"),
                         {"id": tid})
        await db.commit()
    assert await sweep_expired() >= 1
    r = await client.post("/bookings/reserve", json={"ticket_id": str(tid)})
    assert r.status_code == 200
    await client.post("/bookings/release", json={"ticket_id": str(tid)})
