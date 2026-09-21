"""CLI for rebuilding the reviewed public retrieval corpus.

Designed for a future n8n/CI job: it is offline and deterministic, rather
than an unauthenticated HTTP action on the public API.
"""

from __future__ import annotations

import argparse

from sqlalchemy.orm import Session

from career_agent.db.session import create_database_engine
from career_agent.retrieval.chunks import rebuild_public_claim_chunks


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild public retrieval chunks from approved evidence."
    )
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    with Session(engine) as session:
        count = rebuild_public_claim_chunks(session)
        session.commit()
    print(f"rebuilt {count} public claim/source chunks")


if __name__ == "__main__":
    main()
