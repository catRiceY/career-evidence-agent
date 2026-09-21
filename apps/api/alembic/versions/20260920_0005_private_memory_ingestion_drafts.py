"""Add private memory and human-reviewed automation draft queue.

Revision ID: 20260920_0005
Revises: 20260919_0004
"""

from alembic import op
import sqlalchemy as sa

revision = "20260920_0005"
down_revision = "20260919_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "career_memories",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("kind IN ('career_preference', 'interview_reflection', 'jd_note')"),
        sa.CheckConstraint("visibility = 'private'"),
    )
    op.create_index("ix_career_memories_owner_id", "career_memories", ["owner_id"])
    op.create_table(
        "ingestion_drafts",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('pending_review', 'accepted', 'rejected')"),
    )
    op.create_index("ix_ingestion_drafts_owner_id", "ingestion_drafts", ["owner_id"])
    op.create_index("ix_ingestion_drafts_status", "ingestion_drafts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_drafts_status", table_name="ingestion_drafts")
    op.drop_index("ix_ingestion_drafts_owner_id", table_name="ingestion_drafts")
    op.drop_table("ingestion_drafts")
    op.drop_index("ix_career_memories_owner_id", table_name="career_memories")
    op.drop_table("career_memories")
