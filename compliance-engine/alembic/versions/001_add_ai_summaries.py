"""add_ai_summaries_table

Revision ID: 001_add_ai_summaries
Revises: 
Create Date: 2026-09-11

Adds ai_summaries table for persisting AI executive summaries.
Used for thesis experiment data — tracks Gemini latency and quality over time.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = "001_add_ai_summaries"
down_revision = None  # Set this to your previous migration revision if exists
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create ai_summaries table."""
    op.create_table(
        "ai_summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("strategy", sa.String(50), nullable=False, default="executive_summary"),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Index for querying latest summary per scan
    op.create_index(
        "ix_ai_summaries_scan_id",
        "ai_summaries",
        ["scan_id"],
    )
    op.create_index(
        "ix_ai_summaries_created_at",
        "ai_summaries",
        ["created_at"],
    )


def downgrade() -> None:
    """Drop ai_summaries table."""
    op.drop_index("ix_ai_summaries_created_at", table_name="ai_summaries")
    op.drop_index("ix_ai_summaries_scan_id", table_name="ai_summaries")
    op.drop_table("ai_summaries")
