# Architecture Decision Records — Cinema Ticket Booking (سینما بلیت)

13 ADRs. Status: all accepted. Context: Persian cinema seat booking, FastAPI + Postgres, demo for non-technical evaluator.

## ADR-001: Monolith, 3 routers + 2 services
Decision: single FastAPI app. Routers thin HTTP (`routers/`), logic in `services/booking.py`, payment seam `services/payment.py`, janitor `tasks.py`.
Why: team of one, deploy of one, no cross-service transactions. Routers never SQL; service owns state machine.
Rejected: microservices (no independent scaling need), Django (heavier than needed).
Consequence: `main.py` stays wiring only; new outcomes touch one file.

## ADR-002: Async SQLAlchemy + asyncpg, pool 10+20
Decision: async engine, `pool_pre_ping`, pool_size=10 max_overflow=20; SQLite skips pooling; `expire_on_commit=False`.
Why: booking I/O-bound; reserve storms need concurrency without thread-per-request. pre_ping survives Docker restarts.
Consequence: all DB code async; tests use same async path.

## ADR-003: Postgres as concurrency primitive
Decision: Postgres 16 via compose, UUID PKs (non-enumerable), `TIMESTAMP(timezone=True)`, `Numeric(10,2)` money, trigram extension.
Why: need row-level atomic UPDATE + GIN headroom; UUIDs safe in URLs; tz-aware avoids naive/aware 500s.
Consequence: tests run against real Postgres (SQLite would not prove atomicity).

## ADR-004: Reserve-then-confirm, 10-min TTL, 60s sweeper
Decision: two-phase hold. TTL + sweep interval from env (`RESERVATION_TTL_MINUTES=10`, `SWEEP_INTERVAL_SECONDS=60`).
Why: contended seats need hold-while-paying. Expiry enforced 3x: atomic re-reserve SQL, confirm cutoff, sweeper backstop for abandoned holds (closed tab).
Consequence: `200 reserved + expires_at`; client countdown; `410` frees seat inline.

## ADR-005: Atomic UPDATE…WHERE, no Python locks
Decision: reserve = single `UPDATE … WHERE id IN … AND (available OR expired-reserved) RETURNING`. Row count mismatch → rollback → 409.
Why: read-then-write races double-sell. Postgres serializes; exactly one winner, no locks in Python.
Proof: 5 concurrent reserves → exactly 1×200 + 4×409 (test + demo button).

## ADR-006: Multi-seat all-or-nothing, max 6
Decision: `ticket_id` (legacy) + `ticket_ids` (≤6, deduped in Pydantic). One UPDATE covers batch; partial hold impossible.
Why: cinema buyers come in groups; 6 caps abuse + keeps UPDATE bounded. Single-seat kept for backward compat.
Consequence: `422` over 6; mixed batch with one taken seat → whole batch 409.

## ADR-007: Semantic status codes 409/410/402
Decision: 409 taken, 410 expired-and-freed, 402 pay-fail-and-freed; release always 200 idempotent.
Why: client needs distinct UX (pick another vs retry vs re-reserve). 410 vs 409 distinction deliberate.
Consequence: confirm checks hold → window → payment, in that order; never charges dead hold.

## ADR-008: Honest payment stub
Decision: `process_payment` sync pure (`token != "fail"`), TODO marks Stripe spot.
Why: sync — no I/O, async adds nothing. `"fail"` drives 402 path without sandbox. One-file swap later.
Known gap: charge-then-crash window; fix = idempotency key + webhook reconciler (documented, not built).

## ADR-009: Raw SQL writes, ORM reads
Decision: reads ORM + `selectinload` (no N+1); writes raw `text()` so atomicity visible in one statement.
Why: ORM cannot express conditional atomic UPDATE cleanly; raw keeps lock semantics auditable.
Consequence: TTL string interpolated server-side only; IDs always bound params.

## ADR-010: Cinema domain mapped onto 4 existing tables
Decision: venues→Cinema, performers→Movie (+director/year via migration 0002), events→Showtime, tickets→Seat (regular/vip, `B-3`). Table names kept.
Why: schema already fit; rename = migration churn for zero behavior gain. Meaning documented in `models.py`.
Consequence: README notes legacy names; `event_type` mirrors genre.

## ADR-011: Persian-first UX, English API
Decision: UI `lang="fa" dir="rtl"`, Persian strings/errors, fa-IR numerals, toman + separators, Jalali via `Intl fa-IR` 24h; JSON keys + URLs English; `/docs` summaries Persian. System-local fonts only (no CDN).
Why: evaluator non-technical Iranian professor; offline-safe. API stays English for tooling compat.
Consequence: `app/fa.py` normalization (ي/ی ك/ک ة/ه, half-space→space, fa/ar digits→ASCII; search space→`%` wildcard).

## ADR-012: Zero-ID tester flow in single demo.html
Decision: click movie card → showtime → seat map; countdown timer; two payment buttons; plain-language errors + numeric code; race×5 button; collapsed tech log; 2-min test guide panel.
Why: no copy-paste IDs, no guide needed. Color cards instead of posters (no image licensing/accuracy risk).
Consequence: `GET /` serves demo.html; CORS allow-all marked tighten-in-prod.

## ADR-013: Seed + test strategy
Decision: seed upsert idempotent (venues/performers matched by name; venues owning showtimes skipped — re-runs add only missing rows, never duplicates); 20 Iranian movies (title/director/year/genre only, well-known facts), 12 cinemas (7 Shiraz), 3 non-overlapping slots/venue (15/18/21h across 3 days), 40 seats/showtime. Tests `drop_all/create_all` per run (not migrations) for speed; 14 tests lock race/expiry/402/fa-normalization.
Why: deterministic demo; dialect-specific proofs need real Postgres.
Consequence: run `pytest` wipes demo data → re-run `seed.py`.

## ADR-014: DB optimization — indexes only, no new machinery
Decision: keep Postgres + async SQLAlchemy; add only one partial index `ix_tickets_sweep ON tickets (reserved_at) WHERE status='reserved'` (migration 0003). Everything else already covered: trigram GIN `ix_events_name_trgm` (persian ILIKE term search), btree `ix_events_starts_at` + `ix_events_event_type` (date/genre filters + `ORDER BY starts_at`), `ix_venues_city` (city filter join), composite `ix_tickets_event_status (event_id, status)` + `ix_tickets_event_id` (seat-map fetch, atomic reserve WHERE, PK-bound confirm/release by id).
Why: workload is tiny (dozens of showtimes, thousands of seats) and hot paths are fixed-shape — seat-map read + hold-by-PK + windowed list + 60s sweeper. The sweeper's `WHERE status='reserved' AND reserved_at < cutoff` was the only full-scan-shaped query with no supporting index (reserved is a thin slice, so partial not full). Alternatives rejected: full `status` index (mostly-available table, wasted), `reserved_at` full index (same waste), Redis lock/queue, partitioning/read-replicas (no scale signal), stored procs/advisory locks (atomic UPDATE already serializes). Rule: measure (EXPLAIN) before adding more; next step if term-search grows is trigram GIN expansion, not FTS.
Consequence: writes pay one narrow index; sweeper + availability checks index-assisted; 0001 downgrade drops indexes `IF EXISTS` (partial downgrade from test-built DB no longer errors).

## Rejected / deferred
- JWT auth → `DEMO_USER_ID` (documented; ownership checks deferred).
- Per-hall seat maps → single 5×8 layout (capacity differs cosmetically).
- Full-text ranking → ILIKE + trigram index headroom (scale upgrade path).
- Lockfile/pinned deps → floors (`>=`) pragmatism; lockfile = senior upgrade.
