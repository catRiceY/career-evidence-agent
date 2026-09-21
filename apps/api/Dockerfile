FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/apps/api/.venv/bin:$PATH"

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock /app/apps/api/
COPY apps/api/src /app/apps/api/src

RUN pip install --no-cache-dir uv \
    && cd /app/apps/api \
    && uv sync --frozen --extra dev

COPY evidence/registry/approved /app/evidence/registry/approved
COPY apps/api/alembic.ini /app/alembic.ini
COPY apps/api/alembic /app/alembic
COPY apps/api/scripts/start_public_api.sh /app/start_public_api.sh

RUN chmod 0555 /app/start_public_api.sh

ENTRYPOINT ["/app/start_public_api.sh"]
