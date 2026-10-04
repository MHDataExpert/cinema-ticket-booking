"""Cinema domain mapped onto 4 tables (table names kept for migration history).

venues     -> Cinema  (name/city/address of the cinema building)
performers -> Movie   (title/genre/director/year; kind stores the genre)
events     -> Showtime (one screening of a movie at a cinema + starts_at)
tickets    -> Seat    (section = regular/vip, seat = row-number e.g. B-3)
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

TicketStatus = Enum("available", "reserved", "booked", name="ticket_status")


class Venue(Base):
    """Cinema building."""

    __tablename__ = "venues"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(255), index=True)
    address: Mapped[str] = mapped_column(String(512))
    capacity: Mapped[int]
    seat_map: Mapped[dict] = mapped_column(JSON, default=dict)
    events: Mapped[list["Event"]] = relationship(back_populates="venue")


class Performer(Base):
    """Movie. kind = genre (e.g. drama/comedy)."""

    __tablename__ = "performers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(50))  # genre
    description: Mapped[str] = mapped_column(Text, default="")
    director: Mapped[str] = mapped_column(Text, default="")
    year: Mapped[int | None] = mapped_column(nullable=True)
    events: Mapped[list["Event"]] = relationship(back_populates="performer")


class Event(Base):
    """Showtime: one screening. event_type mirrors the movie genre."""

    __tablename__ = "events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    starts_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), index=True)
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id"))
    performer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("performers.id"))
    venue: Mapped[Venue] = relationship(back_populates="events")
    performer: Mapped[Performer] = relationship(back_populates="events")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="event")


class Ticket(Base):
    """Seat of a showtime. section = regular/vip, seat = e.g. B-3."""

    __tablename__ = "tickets"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("events.id"), index=True)
    section: Mapped[str] = mapped_column(String(100))
    seat: Mapped[str] = mapped_column(String(50))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(TicketStatus, default="available")
    reserved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    event: Mapped[Event] = relationship(back_populates="tickets")
