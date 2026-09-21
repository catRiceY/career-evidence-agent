"""stdio MCP adapter. Importing domain tools does not require the MCP package."""

from __future__ import annotations

from career_agent.db.session import create_database_engine
from career_agent.mcp.tools import (
    get_public_project_summary_tool,
    list_suggested_hr_questions_tool,
    search_public_evidence_tool,
)


def main() -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:  # pragma: no cover - depends on optional runtime package
        raise RuntimeError("Install project dependencies with `uv sync --extra dev` before starting MCP.") from error

    server = FastMCP("Career Evidence Agent (Public)")

    @server.tool()
    def search_public_evidence(query: str, limit: int = 5) -> list[dict]:
        """Search reviewed public evidence. Never returns private or draft material."""
        with create_database_engine().connect() as connection:
            from sqlalchemy.orm import Session
            with Session(connection) as session:
                return search_public_evidence_tool(session, query, limit)

    @server.tool()
    def get_public_project_summary(evidence_id: str) -> dict | None:
        """Read one reviewed public project/paper summary by evidence ID."""
        with create_database_engine().connect() as connection:
            from sqlalchemy.orm import Session
            with Session(connection) as session:
                return get_public_project_summary_tool(session, evidence_id)

    @server.tool()
    def list_suggested_hr_questions() -> list[str]:
        """List prompts that help a recruiter explore the public portfolio."""
        return list_suggested_hr_questions_tool()

    server.run()


if __name__ == "__main__":
    main()
