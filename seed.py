"""Seed cinema: 12 cinemas, 20 movies, 30 showtimes/day × 3 days = 36 showtimes, seats regular/vip.

Idempotent upsert: venues/performers matched by name, showtimes skipped per
venue that already has any (each venue owns its slots outright). Re-runs add
only missing rows, never duplicates.
Each venue is treated as a single hall; its 3 showtimes fall on 3 different
days, so no two showtimes in one cinema overlap.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.db import SessionLocal
from app.fa import normalize_fa
from app.models import Event, Performer, Ticket, Venue

# (persian title, director, year, genre) — only widely-known facts.
MOVIES = [
    ("جدایی نادر از سیمین", "اصغر فرهادی", 2011, "درام"),
    ("درباره الی", "اصغر فرهادی", 2009, "درام"),
    ("فروشنده", "اصغر فرهادی", 2016, "درام"),
    ("قهرمان", "اصغر فرهادی", 2021, "درام"),
    ("چهارشنبه‌سوری", "اصغر فرهادی", 2006, "درام"),
    ("شهر زیبا", "اصغر فرهادی", 2004, "درام"),
    ("بچه‌های آسمان", "مجید مجیدی", 1997, "درام"),
    ("طعم گیلاس", "عباس کیارستمی", 1997, "درام"),
    ("نمای نزدیک", "عباس کیارستمی", 1990, "درام"),
    ("گاو", "داریوش مهرجویی", 1969, "درام"),
    ("اجاره‌نشین‌ها", "داریوش مهرجویی", 1987, "کمدی"),
    ("مهمان مامان", "داریوش مهرجویی", 2004, "کمدی"),
    ("لیلی با من است", "کمال تبریزی", 1996, "کمدی"),
    ("مارمولک", "کمال تبریزی", 2004, "کمدی"),
    ("اخراجی‌ها", "مسعود ده‌نمکی", 2007, "کمدی"),
    ("ورود آقایان ممنوع", "رامبد جوان", 2011, "کمدی"),
    ("متری شیش‌ونیم", "سعید روستایی", 2019, "جنایی"),
    ("ابد و یک روز", "سعید روستایی", 2016, "اجتماعی"),
    ("آژانس شیشه‌ای", "ابراهیم حاتمی‌کیا", 1998, "دفاع مقدس"),
    ("کلاه‌قرمزی و پسرخاله", "ایرج طهماسب", 1994, "خانوادگی"),
]

CINEMAS = [
    ("پردیس سینمایی آفتاب", "تهران", "خیابان ولیعصر، بالاتر از پارک ساعی", 300),
    ("سینما بهار", "تهران", "میدان انقلاب، خیابان کارگر", 180),
    ("پردیس سینمایی توس", "مشهد", "بلوار وکیل‌آباد", 220),
    ("سینما نقش جهان", "اصفهان", "خیابان چهارباغ عباسی", 160),
    ("پردیس سینمایی شیراز مال", "شیراز", "بزرگراه دکتر حسابی", 320),
    ("سینما سعدی", "شیراز", "خیابان زند", 170),
    ("سینما شیراز", "شیراز", "میدان نمازی", 150),
    ("سینما حافظ", "شیراز", "خیابان حافظ", 140),
    ("پردیس سینمایی خلیج فارس", "شیراز", "بلوار خلیج فارس", 260),
    ("سینما ارگ", "شیراز", "میدان ارگ", 130),
    ("سینما تخت‌جمشید", "شیراز", "خیابان تخت‌جمشید", 120),
    ("سینما ستاره", "تبریز", "خیابان امام", 140),
]

SLOT_HOURS = (15, 18, 21)

REGULAR = Decimal("120000")
VIP = Decimal("220000")


async def main() -> None:
    async with SessionLocal() as db:
        known_venues = dict((await db.execute(select(Venue.name, Venue.id))).all())
        for n, c, a, cap in CINEMAS:
            if n not in known_venues:
                v = Venue(id=uuid.uuid4(), name=n, city=normalize_fa(c),
                          address=a, capacity=cap, seat_map={})
                db.add(v)
                known_venues[n] = v.id
        known_movies = dict((await db.execute(select(Performer.name, Performer.id))).all())
        genre_of = {}
        for t, d, y, g in MOVIES:
            genre_of[t] = g
            if t not in known_movies:
                p = Performer(id=uuid.uuid4(), name=t, kind=g, description="",
                              director=d, year=y)
                db.add(p)
                known_movies[t] = p.id
        await db.flush()
        # venues that already own showtimes are left untouched: no dupes, no overlaps.
        busy = set((await db.execute(select(Event.venue_id))).scalars().all())
        base = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        events, tickets = [], []
        for v_idx, (n, _c, _a, _cap) in enumerate(CINEMAS):
            vid = known_venues[n]
            if vid in busy:
                continue
            for s in range(3):
                title = MOVIES[(v_idx * 3 + s) % len(MOVIES)][0]
                ev = Event(id=uuid.uuid4(), name=title, description="",
                           event_type=genre_of[title],
                           starts_at=base + timedelta(days=s, hours=SLOT_HOURS[s]),
                           venue_id=vid, performer_id=known_movies[title])
                events.append(ev)
                # 5 rows x 8 seats: rows A-C regular, D-E vip
                for row in "ABCDE":
                    vip = row in "DE"
                    for num in range(1, 9):
                        tickets.append(Ticket(id=uuid.uuid4(), event_id=ev.id,
                                              section="vip" if vip else "regular",
                                              seat=f"{row}-{num}",
                                              price=VIP if vip else REGULAR,
                                              status="available"))
        db.add_all(events + tickets)
        await db.commit()
        nv = await db.scalar(select(func.count(Venue.id)))
        nm = await db.scalar(select(func.count(Performer.id)))
        ne = await db.scalar(select(func.count(Event.id)))
        nt = await db.scalar(select(func.count(Ticket.id)))
        print(f"seeded {nm} movies, {nv} cinemas, {ne} showtimes, {nt} seats")


if __name__ == "__main__":
    asyncio.run(main())
