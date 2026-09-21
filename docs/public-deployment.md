# Public deployment boundary

The deployable service is deliberately narrower than the local development
system: it serves public evidence search and public evidence Q&A only.

## What is deployed

- the FastAPI public endpoints under `/v1/public/evidence/*` and `/health`;
- a new PostgreSQL + pgvector database seeded only from
  `evidence/registry/approved/`;
- approved/public cards, claims, public sources, derived chunks and embeddings;
- the public Answer Harness, citation gate, run manifests and optional Langfuse
  telemetry.

## What is not deployed

- `evidence/registry/approved-private/` or any raw paper/report material;
- the local owner token, Memory, JD matching, mock interview or private Studio
  routes;
- n8n and its webhook; it stays local and inactive;
- local Docker volumes, backups and `infra/.env`.

`apps/api/Dockerfile` runs this exact public-only lifecycle:

1. migrate a fresh database;
2. idempotently seed only approved public cards;
3. derive public chunks and their embeddings;
4. start FastAPI after unsetting `CAREER_AGENT_OWNER_TOKEN`.

## Required cloud configuration

Choose a provider that can run a Docker image and provide PostgreSQL with the
`pgvector` extension. Set these as provider secrets, never in Git:

```text
CAREER_AGENT_DATABASE_URL=postgresql+psycopg://...
CAREER_AGENT_EMBEDDING_BASE_URL=https://...
CAREER_AGENT_EMBEDDING_API_KEY=...
CAREER_AGENT_EMBEDDING_MODEL=...
CAREER_AGENT_CHAT_BASE_URL=https://...
CAREER_AGENT_CHAT_API_KEY=...
CAREER_AGENT_CHAT_MODEL=...
LANGFUSE_HOST=https://us.cloud.langfuse.com
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

Do **not** set `CAREER_AGENT_OWNER_TOKEN` on the public service.

Before attaching the future frontend domain, configure its exact origin in the
API's CORS policy and add edge/API rate limits. The public answer route makes
paid model calls, so it must not be exposed without rate limiting.
