from pathlib import Path

import pytest

from app.db import init_db
from app.reports import repository
from app.reports.dependencies import open_db
from app.reports.errors import ReportNotFoundError


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with open_db(db_path) as connection:
        yield connection


def test_create_report_returns_a_full_row(conn):
    report = repository.create_report(conn, "Kickoff")

    assert report["name"] == "Kickoff"
    assert report["logo_file_id"] is None
    assert report["created_at"] == report["updated_at"]
    assert report["id"]
    assert set(report) == {"id", "name", "logo_file_id", "created_at", "updated_at"}


def test_create_report_returns_a_plain_dict(conn):
    assert type(repository.create_report(conn, "Kickoff")) is dict


def test_create_report_gives_each_report_a_unique_id(conn):
    first = repository.create_report(conn, "A")
    second = repository.create_report(conn, "B")

    assert first["id"] != second["id"]


def test_get_report_returns_the_created_report(conn):
    created = repository.create_report(conn, "Kickoff")

    assert repository.get_report(conn, created["id"]) == created


def test_get_report_raises_for_an_unknown_id(conn):
    with pytest.raises(ReportNotFoundError):
        repository.get_report(conn, "missing")


def test_report_exists_reports_presence(conn):
    created = repository.create_report(conn, "Kickoff")

    assert repository.report_exists(conn, created["id"]) is True
    assert repository.report_exists(conn, "missing") is False


def test_require_report_raises_only_for_an_unknown_id(conn):
    created = repository.create_report(conn, "Kickoff")

    repository.require_report(conn, created["id"])

    with pytest.raises(ReportNotFoundError):
        repository.require_report(conn, "missing")


def test_list_reports_is_empty_initially(conn):
    assert repository.list_reports(conn) == []


def test_list_reports_orders_most_recently_updated_first(conn):
    first = repository.create_report(conn, "First")
    repository.create_report(conn, "Second")
    repository.rename_report(conn, first["id"], "First renamed")

    names = [report["name"] for report in repository.list_reports(conn)]

    assert names == ["First renamed", "Second"]


def test_rename_report_updates_the_name_and_the_timestamp(conn):
    created = repository.create_report(conn, "Kickoff")

    renamed = repository.rename_report(conn, created["id"], "Kickoff v2")

    assert renamed["name"] == "Kickoff v2"
    assert renamed["created_at"] == created["created_at"]
    assert renamed["updated_at"] > created["updated_at"]


def test_rename_report_raises_for_an_unknown_id(conn):
    with pytest.raises(ReportNotFoundError):
        repository.rename_report(conn, "missing", "New name")


def test_set_report_logo_stores_the_file_id(conn):
    created = repository.create_report(conn, "Kickoff")

    updated = repository.set_report_logo(conn, created["id"], "file-123")

    assert updated["logo_file_id"] == "file-123"
    assert updated["updated_at"] > created["updated_at"]


def test_set_report_logo_raises_for_an_unknown_id(conn):
    with pytest.raises(ReportNotFoundError):
        repository.set_report_logo(conn, "missing", "file-123")


def test_touch_report_only_moves_the_updated_timestamp(conn):
    created = repository.create_report(conn, "Kickoff")

    repository.touch_report(conn, created["id"])
    touched = repository.get_report(conn, created["id"])

    assert touched["name"] == created["name"]
    assert touched["updated_at"] > created["updated_at"]


def test_touch_report_raises_for_an_unknown_id(conn):
    with pytest.raises(ReportNotFoundError):
        repository.touch_report(conn, "missing")


def test_delete_report_removes_it(conn):
    created = repository.create_report(conn, "Kickoff")

    repository.delete_report(conn, created["id"])

    assert repository.list_reports(conn) == []


def test_delete_report_raises_for_an_unknown_id(conn):
    with pytest.raises(ReportNotFoundError):
        repository.delete_report(conn, "missing")


def test_delete_report_cascades_to_fields_and_sources(conn):
    created = repository.create_report(conn, "Kickoff")
    conn.execute(
        "INSERT INTO report_fields (id, report_id, label, content, sort_order, "
        "is_user_edited) VALUES ('f1', ?, 'Summary', '', 0, 0)",
        (created["id"],),
    )
    conn.execute(
        "INSERT INTO report_sources (id, report_id, file_id, original_name, "
        "cleaned_text, sort_order, created_at) "
        "VALUES ('s1', ?, 'file-1', 'notes.txt', 'text', 0, 't')",
        (created["id"],),
    )

    repository.delete_report(conn, created["id"])

    field_count = conn.execute("SELECT COUNT(*) AS c FROM report_fields").fetchone()
    source_count = conn.execute("SELECT COUNT(*) AS c FROM report_sources").fetchone()
    assert field_count["c"] == 0
    assert source_count["c"] == 0
