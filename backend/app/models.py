from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)

    vehicle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    driver_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    day_folder: Mapped[str | None] = mapped_column(String(32), nullable=True)

    front_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cabin_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    upload_dir: Mapped[str] = mapped_column(Text, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sync_offset_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    report_json_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline_start_iso: Mapped[str | None] = mapped_column(Text, nullable=True)

    events: Mapped[list[Event]] = relationship(back_populates="trip", cascade="all, delete-orphan")
    score: Mapped[Score | None] = relationship(back_populates="trip", cascade="all, delete-orphan", uselist=False)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True)

    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ts_ms_start: Mapped[int] = mapped_column(Integer, nullable=False)
    ts_ms_end: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    stream: Mapped[str] = mapped_column(String(16), default="front", nullable=False)
    clip_name: Mapped[str] = mapped_column(String(255), nullable=False)

    snapshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    clip_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    trip: Mapped[Trip] = relationship(back_populates="events")


class Score(Base):
    __tablename__ = "scores"

    trip_id: Mapped[str] = mapped_column(ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True)
    fatigue_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    distraction_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    lane_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    following_distance_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    trip: Mapped[Trip] = relationship(back_populates="score")
