"""Add privacy-preserving Harness run manifests.

Revision ID: 20260919_0004
Revises: 20260918_0003
Create Date: 2026-09-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260919_0004"
down_revision = "20260918_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run_manifests",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("access_scope", sa.String(length=32), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=256), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("retrieved_claim_ids", sa.JSON(), nullable=False),
        sa.Column("cited_claim_ids", sa.JSON(), nullable=False),
        sa.Column("tool_trace", sa.JSON(), nullable=False),
        sa.Column("citation_pass", sa.Boolean(), nullable=False),
        sa.Column("privacy_pass", sa.Boolean(), nullable=False),
        sa.Column("structure_pass", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("ix_run_manifests_task_type", "run_manifests", ["task_type"])
    op.create_index("ix_run_manifests_status", "run_manifests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_run_manifests_status", table_name="run_manifests")
    op.drop_index("ix_run_manifests_task_type", table_name="run_manifests")
    op.drop_table("run_manifests")
