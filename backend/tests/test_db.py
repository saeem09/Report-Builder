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


def test_deleting_report_cascades_to_report_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
            "VALUES ('report-1', 'Test Report', NULL, '2026-01-01', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO report_fields (id, report_id, label, content, sort_order) "
            "VALUES ('field-1', 'report-1', 'Summary', '', 0)"
        )
        conn.commit()

        conn.execute("DELETE FROM reports WHERE id = 'report-1'")
        conn.commit()

        remaining = conn.execute(
            "SELECT COUNT(*) AS count FROM report_fields WHERE report_id = 'report-1'"
        ).fetchone()
    finally:
        conn.close()

    assert remaining["count"] == 0


def test_report_fields_has_an_is_user_edited_column_defaulting_to_zero(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
            "VALUES ('r1', 'R', NULL, 't', 't')"
        )
        conn.execute(
            "INSERT INTO report_fields (id, report_id, label, content, sort_order) "
            "VALUES ('f1', 'r1', 'Summary', '', 0)"
        )
        conn.commit()
        row = conn.execute(
            "SELECT is_user_edited FROM report_fields WHERE id = 'f1'"
        ).fetchone()
    finally:
        conn.close()

    assert row["is_user_edited"] == 0


def test_report_sources_table_exists_and_cascades(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
            "VALUES ('r1', 'R', NULL, 't', 't')"
        )
        conn.execute(
            "INSERT INTO report_sources (id, report_id, file_id, original_name, "
            "cleaned_text, sort_order, created_at) "
            "VALUES ('s1', 'r1', 'file-1', 'notes.txt', 'text', 0, 't')"
        )
        conn.commit()

        conn.execute("DELETE FROM reports WHERE id = 'r1'")
        conn.commit()

        remaining = conn.execute(
            "SELECT COUNT(*) AS count FROM report_sources"
        ).fetchone()
    finally:
        conn.close()

    assert remaining["count"] == 0
