import sqlite3
from pathlib import Path

import pytest

from app.db import DB_PATH, init_db
from app.reports.dependencies import get_db_path, get_uploads_dir, open_db
from app.reports.errors import (
    FieldNotFoundError,
    FieldOrderMismatchError,
    NoSourceDocumentsError,
    PdfExportError,
    ReportError,
    ReportNotFoundError,
)
from app.reports.records import new_id, row_to_dict, rows_to_dicts, utc_now_iso
from app.storage import UPLOADS_DIR


def test_get_db_path_returns_the_application_database_path():
    assert get_db_path() == DB_PATH


def test_get_uploads_dir_returns_the_application_uploads_directory():
    assert get_uploads_dir() == UPLOADS_DIR


def test_open_db_commits_on_success(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with open_db(db_path) as conn:
        conn.execute(
            "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
            "VALUES ('r1', 'R', NULL, 't', 't')"
        )

    with open_db(db_path) as verify_conn:
        row = verify_conn.execute(
            "SELECT name FROM reports WHERE id = 'r1'"
        ).fetchone()

    assert row["name"] == "R"


def test_open_db_rolls_back_and_reraises_on_failure(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with pytest.raises(RuntimeError):
        with open_db(db_path) as conn:
            conn.execute(
                "INSERT INTO reports (id, name, logo_file_id, created_at, "
                "updated_at) VALUES ('r1', 'R', NULL, 't', 't')"
            )
            raise RuntimeError("boom")

    with open_db(db_path) as verify_conn:
        count = verify_conn.execute(
            "SELECT COUNT(*) AS count FROM reports"
        ).fetchone()

    assert count["count"] == 0


def test_open_db_closes_the_connection(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with open_db(db_path) as conn:
        pass

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_open_db_enables_foreign_keys(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with open_db(db_path) as conn:
        row = conn.execute("PRAGMA foreign_keys").fetchone()

    assert row[0] == 1


def test_new_id_is_unique_per_call():
    assert new_id() != new_id()


def test_utc_now_iso_is_sortable_utc_with_microseconds():
    first = utc_now_iso()
    second = utc_now_iso()

    assert first.endswith("Z")
    assert "T" in first
    assert "." in first
    assert first <= second


def test_row_to_dict_returns_none_for_none():
    assert row_to_dict(None) is None


def test_row_to_dict_and_rows_to_dicts_return_plain_dicts(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)

    with open_db(db_path) as conn:
        conn.execute(
            "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
            "VALUES ('r1', 'R', NULL, 't', 't')"
        )
        row = conn.execute("SELECT id, name FROM reports").fetchone()
        rows = conn.execute("SELECT id, name FROM reports").fetchall()

    assert row_to_dict(row) == {"id": "r1", "name": "R"}
    assert rows_to_dicts(rows) == [{"id": "r1", "name": "R"}]
    assert type(row_to_dict(row)) is dict


def test_error_hierarchy():
    for error_class in (
        ReportNotFoundError,
        FieldNotFoundError,
        FieldOrderMismatchError,
        NoSourceDocumentsError,
        PdfExportError,
    ):
        assert issubclass(error_class, ReportError)
    assert issubclass(ReportError, Exception)
