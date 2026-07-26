from pathlib import Path

from app.db import get_connection, init_db


def test_init_db_creates_expected_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}
    finally:
        conn.close()

    assert {"reports", "report_fields", "diagrams", "files"}.issubset(table_names)
