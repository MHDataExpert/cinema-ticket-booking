# Cinema Ticket Booking — سینما بلیت

Persian cinema seat-booking API + zero-guide demo UI. FastAPI + Postgres + SQLAlchemy async.

**Flow:** search movies → pick showtime → click seats on seat map → 10-minute hold → pay or release.

- Demo UI: open `http://localhost:8000/` after boot (Persian, RTL, no IDs to copy)
- API docs: `http://localhost:8000/docs`
- Decisions: [`docs/ADR.md`](docs/ADR.md) (13 records — why every choice was made)

## Quickstart

```bash
docker compose up -d
pip install -r requirements.txt
alembic upgrade head# on Windows PowerShell: $env:PYTHONPATH="."; alembic upgrade head
python seed.py          # 12 movies, 9 cinemas, 27 showtimes, 1080 seats
uvicorn app.main:app   # or: python -m uvicorn app.main:app --port 8000
```

Then open http://localhost:8000/ and follow the 2-minute test guide on the page.

Config via `.env` (see `.env.example`): `DATABASE_URL`, `DEMO_USER_ID`,
`RESERVATION_TTL_MINUTES=10`, `SWEEP_INTERVAL_SECONDS=60`.

## API

| Call | Success | Failure |
|---|---|---|
| `GET /search?term=&city=&event_type=&date_from=&date_to=&limit=&offset=` | 200 list + `min_price` | — |
| `GET /events/{id}` | 200 venue, movie, seats | 404 showtime not found |
| `POST /bookings/reserve` `{"ticket_id"}` or `{"ticket_ids":[…]}` (≤6, all-or-nothing) | 200 `reserved` + `expires_at` | 409 seat taken |
| `PUT /bookings/confirm` `{ids…, "payment_token"}` | 200 `booked` | 410 expired (freed) · 402 pay failed (freed) · 409 taken |
| `POST /bookings/release` | 200 `available` (idempotent) | — |
| `GET /health` | 200 `{"ok": true}` | — |

Field names and URLs stay English; human messages and `/docs` descriptions are Persian.
Persian search input is normalized (ي/ی، ك/ک، half-space, Persian/Arabic digits).

## Test

```bash
pytest   # needs Postgres up; 14 tests: race, expiry, 402, multi-seat, fa-search
```

⚠️ Tests `drop_all/create_all`, so they wipe demo data — re-run `python seed.py` after.

## Project layout

```
app/main.py            wiring, lifespan sweeper, serves demo.html at /
app/routers/           search.py · events.py · bookings.py (thin HTTP)
app/services/booking.py  atomic reserve/confirm/release (the brain)
app/services/payment.py  stub: only token "fail" fails (Stripe seam)
app/tasks.py           60s expiry sweeper (backup; reserve/confirm check inline)
app/fa.py              Persian search normalization
app/models.py          4 tables (venues/cinemas, performers/movies, events/showtimes, tickets/seats)
app/schemas.py         request/response shapes, max 6 seats/order
seed.py                idempotent demo data (12 real movies, 9 fictional cinemas)
demo.html              Persian RTL demo UI (served at /)
docs/ADR.md            architecture decision records
alembic/versions/      0001 schema · 0002 movie director/year
tests/                 conftest fixtures + test_api (12) + test_fa (2)
```

## Known limits (by design, see ADR)

- No auth — all bookings stamp `DEMO_USER_ID`.
- Payment is a stub; crash-between-charge-and-commit needs idempotency keys + webhook reconciler.
- Single 5×8 seat layout for all halls; ILIKE search (trigram index ready for scale).
- CORS allow-all is for the local demo; tighten in prod.
