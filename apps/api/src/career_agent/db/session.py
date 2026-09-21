from __future__ import annotations

import os

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def _normalize_postgres_driver(value: str) -> str:
    """Use psycopg v3 for provider URLs that omit a SQLAlchemy driver.

    Railway exposes ``postgresql://...`` in ``DATABASE_URL``.  This project
    installs the psycopg v3 driver, whose explicit SQLAlchemy URL is
    ``postgresql+psycopg://...``.  Keeping the conversion here means the API
    and Alembic migrations always connect the same way.
    """

    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


def database_url() -> str:
    """Read an explicit URL, or construct the configured local Compose URL.

    The fallback only exists when all local PostgreSQL variables are present;
    it never supplies a password or production host implicitly.
    """

    value = os.environ.get("CAREER_AGENT_DATABASE_URL")
    if value:
        return _normalize_postgres_driver(value)
    required = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    if all(os.environ.get(name) for name in required):
        return URL.create(
            "postgresql+psycopg",
            username=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.environ.get("POSTGRES_PORT", "54329")),
            database=os.environ["POSTGRES_DB"],
        ).render_as_string(hide_password=False)
    raise RuntimeError("configure CAREER_AGENT_DATABASE_URL or local POSTGRES_* variables")


def create_database_engine(url: str | None = None) -> Engine:
    # Command-line maintenance jobs pass an explicit URL to this function.
    # Apply the same provider-URL normalization used for environment values so
    # Railway's ``postgresql://`` URL never falls back to the absent psycopg2
    # driver during seeding or embedding refresh.
    resolved_url = _normalize_postgres_driver(url) if url else database_url()
    return create_engine(resolved_url, pool_pre_ping=True)


def create_session_factory(url: str | None = None) -> sessionmaker[Session]:
    return sessionmaker(bind=create_database_engine(url), autoflush=False, expire_on_commit=False)
