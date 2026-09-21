"""Add rebuildable source-cited retrieval chunks.

Revision ID: 20260918_0002
Revises: 20260918_0001
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260918_0002"
down_revision = "20260918_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_chunks",
        sa.Column("id", sa.String(length=256), primary_key=True),
        sa.Column("claim_id", sa.String(length=128), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", sa.String(length=128), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("chunk_strategy", sa.String(length=64), nullable=False),
        sa.Column("index_visibility", sa.String(length=32), nullable=False),
        sa.Column("source_locator", sa.Text()),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("index_visibility IN ('public', 'private')"),
        sa.CheckConstraint("chunk_strategy IN ('claim_source_v1')"),
    )
    op.create_index("ix_evidence_chunks_claim_id", "evidence_chunks", ["claim_id"])
    op.create_index("ix_evidence_chunks_source_id", "evidence_chunks", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_chunks_source_id", table_name="evidence_chunks")
    op.drop_index("ix_evidence_chunks_claim_id", table_name="evidence_chunks")
    op.drop_table("evidence_chunks")
