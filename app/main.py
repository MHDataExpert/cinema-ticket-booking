import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.routers import bookings, events, search
from app.tasks import sweeper_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sweeper_loop())
    yield
    task.cancel()


app = FastAPI(
    title="سینما بلیت",
    description="رزرو و خرید بلیت سینما: جست‌وجوی فیلم، انتخاب سانس، رزرو ۱۰ دقیقه‌ای صندلی، پرداخت یا آزادسازی.",
    version="2.0.0",
    lifespan=lifespan,
)
# ponytail: allow-all for local demo; tighten in prod.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(events.router)
app.include_router(search.router)
app.include_router(bookings.router)


@app.get("/health", summary="سلامتی سرویس", description="اگر سرویس روشن باشد «ok» برمی‌گرداند.")
async def health():
    return {"ok": True}


@app.get("/", include_in_schema=False)
async def demo_page():
    return FileResponse(Path(__file__).resolve().parent.parent / "demo.html")
