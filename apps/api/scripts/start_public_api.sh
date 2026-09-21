#!/bin/sh
set -eu

: "${CAREER_AGENT_DATABASE_URL:?set CAREER_AGENT_DATABASE_URL}"
: "${CAREER_AGENT_EMBEDDING_BASE_URL:?set CAREER_AGENT_EMBEDDING_BASE_URL}"
: "${CAREER_AGENT_EMBEDDING_API_KEY:?set CAREER_AGENT_EMBEDDING_API_KEY}"

# A public image must never register owner-only routes.
unset CAREER_AGENT_OWNER_TOKEN

alembic upgrade head
python -m career_agent.evidence.seed_public_deployment \
  --database-url "$CAREER_AGENT_DATABASE_URL" \
  --cards-dir /app/evidence/registry/approved
python -m career_agent.retrieval.rebuild_chunks --database-url "$CAREER_AGENT_DATABASE_URL"
python -m career_agent.retrieval.refresh_embeddings --database-url "$CAREER_AGENT_DATABASE_URL"

exec uvicorn career_agent.api.main:create_app --factory --host 0.0.0.0 --port "${PORT:-8000}"
