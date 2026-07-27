from fastapi.testclient import TestClient

from app.db import get_connection, init_db as real_init_db
from app.main import app

client = TestClient(app)


def init_db_recorder(db_path):
    """Run the real init_db against a temp path instead of data/app.db."""
    real_init_db(db_path)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_lifespan_initializes_the_database(tmp_path, monkeypatch):
    db_path = tmp_path / "lifespan.db"
    monkeypatch.setattr("app.main.init_db", lambda: init_db_recorder(db_path))

    with TestClient(app):
        pass

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}
    finally:
        conn.close()

    assert {"reports", "report_fields", "report_sources", "files"}.issubset(
        table_names
    )
