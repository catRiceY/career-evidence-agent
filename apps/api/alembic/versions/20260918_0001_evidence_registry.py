"""Create the reviewed evidence registry.

Revision ID: 20260918_0001
Revises:
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa


revision = "20260918_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_cards",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("version", sa.String(length=32), nullable=False, server_default="0.1"),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("period", sa.String(length=128)),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("answer_visibility", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("source_visibility_default", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("personal_contribution_status", sa.String(length=32), nullable=False, server_default="needs_confirmation"),
        sa.Column("role", sa.String(length=512)),
        sa.Column("tech_stack", sa.JSON(), nullable=False),
        sa.Column("target_tracks", sa.JSON(), nullable=False),
        sa.Column("priority_by_track", sa.JSON(), nullable=False),
        sa.Column("status_notes", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("next_evidence_to_add", sa.JSON(), nullable=False),
        sa.Column("paper_metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("type IN ('project', 'paper', 'system_module', 'experience')"),
        sa.CheckConstraint("review_status IN ('draft', 'in_review', 'approved', 'rejected')"),
        sa.CheckConstraint("answer_visibility IN ('public', 'private', 'exclude')"),
        sa.CheckConstraint("personal_contribution_status IN ('needs_confirmation', 'confirmed', 'not_applicable', 'team_only')"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("evidence_id", sa.String(length=128), sa.ForeignKey("evidence_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("url_or_path", sa.Text(), nullable=False),
        sa.Column("source_visibility", sa.String(length=32), nullable=False),
        sa.Column("allowed_quote_scope", sa.String(length=32), nullable=False, server_default="none"),
        sa.Column("locator", sa.Text()),
        sa.Column("version_ref", sa.String(length=256)),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.CheckConstraint("source_visibility IN ('public', 'private', 'restricted')"),
        sa.CheckConstraint("allowed_quote_scope IN ('none', 'short_summary', 'paragraph', 'full_public')"),
    )
    op.create_index("ix_sources_evidence_id", "sources", ["evidence_id"])
    op.create_table(
        "claims",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("evidence_id", sa.String(length=128), sa.ForeignKey("evidence_cards.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.String(length=64), nullable=False),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("answer_visibility", sa.String(length=32), nullable=False, server_default="private"),
        sa.Column("personal_contribution_status", sa.String(length=32), nullable=False, server_default="needs_confirmation"),
        sa.Column("evidence_strength", sa.String(length=32), nullable=False, server_default="weak"),
        sa.Column("hr_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("risk_or_limit", sa.Text(), nullable=False, server_default=""),
        sa.Column("target_tracks", sa.JSON(), nullable=False),
        sa.Column("created_from", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("review_status IN ('draft', 'in_review', 'approved', 'rejected')"),
        sa.CheckConstraint("answer_visibility IN ('public', 'private', 'exclude')"),
        sa.CheckConstraint("personal_contribution_status IN ('needs_confirmation', 'confirmed', 'not_applicable', 'team_only')"),
        sa.CheckConstraint("evidence_strength IN ('strong', 'medium', 'weak')"),
    )
    op.create_index("ix_claims_evidence_id", "claims", ["evidence_id"])
    op.create_table(
        "claim_sources",
        sa.Column("claim_id", sa.String(length=128), sa.ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("source_id", sa.String(length=128), sa.ForeignKey("sources.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("locator", sa.Text()),
    )
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.String(length=128), primary_key=True),
        sa.Column("claim_id", sa.String(length=128), sa.ForeignKey("claims.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("decision", sa.String(length=32), nullable=False),
        sa.Column("previous_review_status", sa.String(length=32), nullable=False),
        sa.Column("previous_answer_visibility", sa.String(length=32), nullable=False),
        sa.Column("next_review_status", sa.String(length=32), nullable=False),
        sa.Column("next_answer_visibility", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("decision IN ('approved', 'rejected', 'needs_changes')"),
    )
    op.create_index("ix_review_decisions_claim_id", "review_decisions", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_review_decisions_claim_id", table_name="review_decisions")
    op.drop_table("review_decisions")
    op.drop_table("claim_sources")
    op.drop_index("ix_claims_evidence_id", table_name="claims")
    op.drop_table("claims")
    op.drop_index("ix_sources_evidence_id", table_name="sources")
    op.drop_table("sources")
    op.drop_table("evidence_cards")
