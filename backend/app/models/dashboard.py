"""Dashboard, panel, and variable ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    grafana_uid: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512))
    folder: Mapped[str | None] = mapped_column(String(512), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    json_hash: Mapped[str] = mapped_column(String(64))
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    panels: Mapped[list[DashboardPanel]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    variables: Mapped[list[DashboardVariable]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DashboardPanel(Base):
    __tablename__ = "dashboard_panels"
    __table_args__ = (
        UniqueConstraint("dashboard_id", "grafana_panel_id", name="uq_panel_per_dashboard"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        index=True,
    )
    grafana_panel_id: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(512))
    panel_type: Mapped[str] = mapped_column(String(128))
    datasource_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    dashboard: Mapped[Dashboard] = relationship(back_populates="panels")


class DashboardVariable(Base):
    __tablename__ = "dashboard_variables"
    __table_args__ = (
        UniqueConstraint("dashboard_id", "name", name="uq_variable_per_dashboard"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dashboard_id: Mapped[int] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variable_type: Mapped[str] = mapped_column(String(64))
    query: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_value: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    multi: Mapped[bool] = mapped_column(Boolean, default=False)
    include_all: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_definition: Mapped[dict[str, Any]] = mapped_column(JSONB)

    dashboard: Mapped[Dashboard] = relationship(back_populates="variables")
