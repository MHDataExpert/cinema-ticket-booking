from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.schemas import ConfirmIn, ReleaseIn, ReserveIn
from app.services.booking import confirm_tickets, release_tickets, reserve_tickets

router = APIRouter()

NOT_AVAILABLE = "این صندلی قبلاً گرفته شده است؛ لطفاً صندلی دیگری انتخاب کنید"


@router.post(
    "/bookings/reserve",
    summary="رزرو موقت صندلی",
    description="یک تا ۶ صندلی را برای ۱۰ دقیقه نگه می‌دارد (همه یا هیچ‌کدام). صندلی گرفته‌شده خطای ۴۰۹ می‌دهد.",
)
async def reserve(body: ReserveIn, db: AsyncSession = Depends(get_db)):
    ids = body.ids()
    exp = await reserve_tickets(db, ids)
    if not exp:
        raise HTTPException(409, NOT_AVAILABLE)
    out = {"ticket_ids": ids, "status": "reserved", "expires_at": exp}
    if len(ids) == 1:
        out["ticket_id"] = ids[0]
    return out


@router.put(
    "/bookings/confirm",
    summary="تأیید و پرداخت",
    description="رزرو را قطعی می‌کند. تأخیر بیش از ۱۰ دقیقه خطای ۴۱۰ و پرداخت ناموفق خطای ۴۰۲ می‌دهد (در هر دو حالت صندلی آزاد می‌شود).",
)
async def confirm(body: ConfirmIn, db: AsyncSession = Depends(get_db)):
    code, payload = await confirm_tickets(db, body.ids(), body.payment_token)
    if code != 200:
        raise HTTPException(code, payload["detail"])
    return payload


@router.post(
    "/bookings/release",
    summary="آزادسازی صندلی",
    description="رزرو را لغو و صندلی را آزاد می‌کند. همیشه موفق است.",
)
async def release(body: ReleaseIn, db: AsyncSession = Depends(get_db)):
    ids = body.ids()
    await release_tickets(db, ids)
    out: dict = {"ticket_ids": ids, "status": "available"}
    if len(ids) == 1:
        out["ticket_id"] = ids[0]
    return out
