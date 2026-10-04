from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


_engine_kw = {"pool_pre_ping": True}
if "sqlite" not in settings.database_url:
    _engine_kw.update(pool_size=10, max_overflow=20)
engine = create_async_engine(settings.database_url, **_engine_kw)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session:
        yield session
