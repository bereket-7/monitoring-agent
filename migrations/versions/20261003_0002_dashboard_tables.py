"""Create dashboard, panel, and variable tables.

Revision ID: 20261003_0002
Revises: 20260328_0001
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261003_0002"
down_revision: str | None = "20260328_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dashboards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("grafana_uid", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("folder", sa.String(length=512), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("json_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grafana_uid"),
    )
    op.create_index("ix_dashboards_grafana_uid", "dashboards", ["grafana_uid"])

    op.create_table(
        "dashboard_panels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("grafana_panel_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("panel_type", sa.String(length=128), nullable=False),
        sa.Column("datasource_uid", sa.String(length=255), nullable=True),
        sa.Column(
            "raw_definition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dashboard_id",
            "grafana_panel_id",
            name="uq_panel_per_dashboard",
        ),
    )
    op.create_index("ix_dashboard_panels_dashboard_id", "dashboard_panels", ["dashboard_id"])

    op.create_table(
        "dashboard_variables",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dashboard_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("variable_type", sa.String(length=64), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("current_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("multi", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "include_all",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "raw_definition",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["dashboard_id"], ["dashboards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dashboard_id", "name", name="uq_variable_per_dashboard"),
    )
    op.create_index(
        "ix_dashboard_variables_dashboard_id",
        "dashboard_variables",
        ["dashboard_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_variables_dashboard_id", table_name="dashboard_variables")
    op.drop_table("dashboard_variables")
    op.drop_index("ix_dashboard_panels_dashboard_id", table_name="dashboard_panels")
    op.drop_table("dashboard_panels")
    op.drop_index("ix_dashboards_grafana_uid", table_name="dashboards")
    op.drop_table("dashboards")
