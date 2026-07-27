from pathlib import Path

import pytest

from app.db import init_db
from app.reports import repository, sources
from app.reports.dependencies import open_db
from app.reports.errors import ReportNotFoundError


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with open_db(db_path) as connection:
        yield connection


@pytest.fixture()
def report_id(conn):
    return repository.create_report(conn, "Kickoff")["id"]


def test_list_sources_is_empty_for_a_new_report(conn, report_id):
    assert sources.list_sources(conn, report_id) == []


def test_add_source_returns_a_full_row(conn, report_id):
    source = sources.add_source(
        conn, report_id, "file-1", "meeting-one.txt", "Cleaned text."
    )

    assert source["report_id"] == report_id
    assert source["file_id"] == "file-1"
    assert source["original_name"] == "meeting-one.txt"
    assert source["cleaned_text"] == "Cleaned text."
    assert source["sort_order"] == 0
    assert source["created_at"]


def test_add_source_raises_for_an_unknown_report(conn):
    with pytest.raises(ReportNotFoundError):
        sources.add_source(conn, "missing", "file-1", "a.txt", "text")


def test_sources_accumulate_across_meetings_in_upload_order(conn, report_id):
    sources.add_source(conn, report_id, "f1", "meeting-one.txt", "First meeting.")
    sources.add_source(conn, report_id, "f2", "meeting-two.txt", "Second meeting.")
    sources.add_source(conn, report_id, "f3", "meeting-three.txt", "Third meeting.")

    stored = sources.list_sources(conn, report_id)

    assert [source["original_name"] for source in stored] == [
        "meeting-one.txt",
        "meeting-two.txt",
        "meeting-three.txt",
    ]
    assert [source["sort_order"] for source in stored] == [0, 1, 2]


def test_add_source_bumps_the_report_timestamp(conn, report_id):
    before = repository.get_report(conn, report_id)["updated_at"]

    sources.add_source(conn, report_id, "f1", "a.txt", "text")

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_list_sources_ignores_other_reports(conn, report_id):
    other_id = repository.create_report(conn, "Other")["id"]
    sources.add_source(conn, report_id, "f1", "mine.txt", "mine")
    sources.add_source(conn, other_id, "f2", "theirs.txt", "theirs")

    stored = sources.list_sources(conn, report_id)

    assert [source["original_name"] for source in stored] == ["mine.txt"]


def test_record_file_stores_metadata(conn):
    record = sources.record_file(conn, "file-1", "logo.png", "image/png")

    assert record["id"] == "file-1"
    assert record["original_name"] == "logo.png"
    assert record["content_type"] == "image/png"
    assert record["stored_path"] == "file-1/logo.png"
    assert record["created_at"]


def test_record_file_sanitizes_the_stored_path(conn):
    record = sources.record_file(conn, "file-1", "../../escaped.txt", "text/plain")

    assert record["stored_path"] == "file-1/escaped.txt"


def test_get_file_record_round_trips(conn):
    sources.record_file(conn, "file-1", "logo.png", "image/png")

    assert sources.get_file_record(conn, "file-1")["original_name"] == "logo.png"


def test_get_file_record_returns_none_for_an_unknown_id(conn):
    assert sources.get_file_record(conn, "missing") is None


def test_record_file_replaces_an_existing_row_for_the_same_id(conn):
    sources.record_file(conn, "file-1", "old.png", "image/png")

    sources.record_file(conn, "file-1", "new.png", "image/jpeg")

    assert sources.get_file_record(conn, "file-1")["original_name"] == "new.png"


def test_deleting_a_report_cascades_to_its_sources(conn, report_id):
    sources.add_source(conn, report_id, "f1", "a.txt", "text")

    repository.delete_report(conn, report_id)

    assert conn.execute("SELECT COUNT(*) AS c FROM report_sources").fetchone()["c"] == 0
