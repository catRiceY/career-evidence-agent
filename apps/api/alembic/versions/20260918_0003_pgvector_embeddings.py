"""Add PostgreSQL-only storage for rebuildable chunk embeddings.

Revision ID: 20260918_0003
Revises: 20260918_0002
Create Date: 2026-09-18
"""

from alembic import op


revision = "20260918_0003"
down_revision = "20260918_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Install vector storage only when the database is PostgreSQL.

    SQLite remains the fast contract-test database. It intentionally has no
    pseudo-vector implementation, because a fake vector backend would hide
    production-specific index and dimension behaviour.
    """

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE chunk_embeddings (
            chunk_id VARCHAR(256) NOT NULL REFERENCES evidence_chunks(id) ON DELETE CASCADE,
            embedding_model VARCHAR(256) NOT NULL,
            embedding_dimensions INTEGER NOT NULL CHECK (embedding_dimensions > 0),
            embedding vector NOT NULL,
            content_hash VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chunk_id, embedding_model)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_chunk_embeddings_model_hash "
        "ON chunk_embeddings (embedding_model, content_hash)"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute("DROP TABLE chunk_embeddings")
