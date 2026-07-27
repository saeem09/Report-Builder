"""Shared FastAPI test harness for the reports API.

Two things here are load-bearing and must not be "simplified":

1. TestClient(app) is constructed WITHOUT the `with` context manager.
   Starlette only runs the lifespan when the client is used as a context
   manager, and app.dependency_overrides does not apply to lifespan handlers.
   Using `with` would therefore run init_db() against the real data/app.db
   during the test run.

2. The test database is a real temp file, never ":memory:". Each route handler
   opens its own connection for its unit of work, and every sqlite3 connection
   to ":memory:" gets a separate, empty database, so ":memory:" cannot work
   with this design at all.
"""

from pathlib import Path
from typing import Tuple

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.reports.dependencies import get_db_path, get_uploads_dir


def build_client(tmp_path: Path) -> Tuple[TestClient, Path]:
    """Return a TestClient wired to a temp database and a temp uploads dir."""
    db_path = tmp_path / "test.db"
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    init_db(db_path)
    app.dependency_overrides[get_db_path] = lambda: db_path
    app.dependency_overrides[get_uploads_dir] = lambda: uploads_dir
    return TestClient(app), db_path


def reset_overrides() -> None:
    """Undo build_client's dependency overrides."""
    app.dependency_overrides.clear()


def create_report(client: TestClient, name: str = "Kickoff", labels=()) -> dict:
    """Create a report through the API and return its ReportDetail body."""
    response = client.post(
        "/api/reports", json={"name": name, "field_labels": list(labels)}
    )
    assert response.status_code == 201, response.text
    return response.json()
