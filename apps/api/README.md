# Career Evidence Agent API

The FastAPI backend implements the Evidence Registry, hybrid retrieval,
evidence-aware generation, citation validation, run auditing and bounded
LangGraph workflows.

## Development

```bash
uv sync --extra dev
uv run --extra dev pytest
```

## Public endpoints

- `GET /health`
- `GET /v1/public/evidence`
- `GET /v1/public/evidence/search?q=...`
- `GET /v1/public/evidence/search/hybrid?q=...`
- `POST /v1/public/evidence/answer`
- `GET /v1/public/evidence/{evidence_id}`

The answer gateway retrieves only reviewed public claims, asks the configured
model for structured statements and rejects citations that are missing,
out-of-scope or absent from the current retrieval result. Successful runs record
a minimal manifest containing hashes, model identity, claim IDs, steps and
timings—not raw questions, answers, secrets or private documents.

## Canonical evidence import

```bash
uv run python -m career_agent.evidence.import_canonical \
  --database-url 'sqlite+pysqlite:////tmp/career-evidence.sqlite' \
  --cards-dir ../../evidence/registry/approved
```

For hybrid retrieval, use PostgreSQL with pgvector and configure an
OpenAI-compatible embedding provider through environment variables. The
public-only Docker entrypoint migrates a fresh database, imports only
`evidence/registry/approved/`, rebuilds public claim chunks and starts the API.

## Workflow code

The repository also includes JD matching, interview planning and
evidence-feedback workflows. Their unit tests use synthetic inputs. No real
private evidence, JD text or interview answer is included in this public
repository, and private HTTP routes are absent unless an explicit local owner
token and model configuration are supplied.

