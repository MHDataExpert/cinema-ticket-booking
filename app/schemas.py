import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

MAX_SEATS_PER_ORDER = 6


class VenueOut(BaseModel):
    id: uuid.UUID
    name: str
    city: str
    address: str
    capacity: int


class PerformerOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    description: str
    director: str = ""
    year: int | None = None


class TicketOut(BaseModel):
    id: uuid.UUID
    section: str
    seat: str
    price: Decimal
    status: str


class EventDetail(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    event_type: str
    starts_at: datetime
    venue: VenueOut
    performer: PerformerOut
    tickets: list[TicketOut]


class EventSummary(BaseModel):
    id: uuid.UUID
    name: str
    event_type: str
    starts_at: datetime
    venue_name: str
    city: str
    performer_name: str
    min_price: Decimal | None


class _SeatList(BaseModel):
    ticket_id: uuid.UUID | None = Field(default=None, description="Single seat (old style)")
    ticket_ids: list[uuid.UUID] | None = Field(default=None, description="Several seats, max 6")

    @model_validator(mode="after")
    def _check(self):
        ids = self.ids()
        if not ids:
            raise ValueError("حداقل یک صندلی انتخاب کنید")
        if len(ids) > MAX_SEATS_PER_ORDER:
            raise ValueError(f"حداکثر {MAX_SEATS_PER_ORDER} صندلی در هر سفارش")
        return self

    def ids(self) -> list[uuid.UUID]:
        seen: list[uuid.UUID] = []
        for t in ([self.ticket_id] if self.ticket_id else []) + (self.ticket_ids or []):
            if t not in seen:
                seen.append(t)
        return seen


class ReserveIn(_SeatList):
    pass


class ReserveOut(BaseModel):
    ticket_id: uuid.UUID | None = None
    ticket_ids: list[uuid.UUID] | None = None
    status: str
    expires_at: datetime


class ConfirmIn(_SeatList):
    payment_token: str


class ConfirmOut(BaseModel):
    ticket_id: uuid.UUID | None = None
    ticket_ids: list[uuid.UUID] | None = None
    status: str


class ReleaseIn(_SeatList):
    pass
