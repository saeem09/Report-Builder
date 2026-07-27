import io
from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides
from document_builders import SINGLE_PAGE_PDF_BYTES, build_docx_bytes

from app.db import get_connection
from app.reports.pipeline_routes import MAX_UPLOAD_BYTES


@pytest.fixture()
def client_and_db(tmp_path: Path):
    test_client, db_path = build_client(tmp_path)
    yield test_client, db_path, tmp_path / "uploads"
    reset_overrides()


@pytest.fixture()
def client(client_and_db):
    return client_and_db[0]


def documents_url(report_id: str) -> str:
    return "/api/reports/{0}/documents".format(report_id)


def upload(client, report_id, name, content, content_type="text/plain"):
    return client.post(
        documents_url(report_id),
        files={"file": (name, io.BytesIO(content), content_type)},
    )


def stored_cleaned_text(db_path: Path, report_id: str):
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT cleaned_text FROM report_sources WHERE report_id = ? "
            "ORDER BY sort_order",
            (report_id,),
        ).fetchall()
    finally:
        conn.close()
    return [row["cleaned_text"] for row in rows]


def test_upload_txt_returns_201_with_the_source_record(client):
    report = create_report(client)

    response = upload(client, report["id"], "notes.txt", b"Kickoff held.")

    assert response.status_code == 201
    body = response.json()
    assert body["report_id"] == report["id"]
    assert body["original_name"] == "notes.txt"
    assert body["sort_order"] == 0
    assert body["file_id"]
    assert "cleaned_text" not in body


def test_upload_stores_cleaned_text(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    upload(client, report["id"], "notes.txt", b"Line   one.\r\n\n\n\nLine two.  ")

    assert stored_cleaned_text(db_path, report["id"]) == ["Line one.\n\nLine two."]


def test_upload_saves_the_original_file_to_the_uploads_directory(client_and_db):
    client, _, uploads_dir = client_and_db
    report = create_report(client)

    body = upload(client, report["id"], "notes.txt", b"Kickoff held.").json()

    saved = uploads_dir / body["file_id"] / "notes.txt"
    assert saved.read_bytes() == b"Kickoff held."


def test_upload_records_the_file_metadata(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    body = upload(client, report["id"], "notes.txt", b"Kickoff held.").json()

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT original_name, content_type FROM files WHERE id = ?",
            (body["file_id"],),
        ).fetchone()
    finally:
        conn.close()
    assert row["original_name"] == "notes.txt"
    assert row["content_type"] == "text/plain"


def test_upload_accepts_html(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    response = upload(
        client,
        report["id"],
        "notes.html",
        b"<html><body><p>Kickoff held.</p></body></html>",
        "text/html",
    )

    assert response.status_code == 201
    assert "Kickoff held." in stored_cleaned_text(db_path, report["id"])[0]


def test_upload_accepts_docx(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    response = upload(
        client,
        report["id"],
        "notes.docx",
        build_docx_bytes(["Kickoff held."]),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert response.status_code == 201
    assert "Kickoff held." in stored_cleaned_text(db_path, report["id"])[0]


def test_upload_accepts_pdf(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    response = upload(
        client, report["id"], "notes.pdf", SINGLE_PAGE_PDF_BYTES, "application/pdf"
    )

    assert response.status_code == 201
    assert "Sprint review notes" in stored_cleaned_text(db_path, report["id"])[0]


def test_multiple_uploads_accumulate_in_order(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)

    upload(client, report["id"], "meeting-one.txt", b"First meeting.")
    upload(client, report["id"], "meeting-two.txt", b"Second meeting.")

    assert stored_cleaned_text(db_path, report["id"]) == [
        "First meeting.",
        "Second meeting.",
    ]


def test_second_upload_gets_the_next_sort_order(client):
    report = create_report(client)
    upload(client, report["id"], "one.txt", b"First.")

    second = upload(client, report["id"], "two.txt", b"Second.")

    assert second.json()["sort_order"] == 1


def test_upload_bumps_the_report_timestamp(client):
    report = create_report(client)

    upload(client, report["id"], "notes.txt", b"Kickoff held.")

    fetched = client.get("/api/reports/{0}".format(report["id"])).json()
    assert fetched["updated_at"] > report["updated_at"]


def test_upload_returns_404_for_an_unknown_report(client):
    response = upload(client, "missing", "notes.txt", b"Kickoff held.")

    assert response.status_code == 404


def test_upload_rejects_an_unsupported_file_type(client):
    response = upload(client, create_report(client)["id"], "notes.rtf", b"data")

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_an_unparseable_document(client):
    response = upload(
        client, create_report(client)["id"], "notes.docx", b"not a real docx"
    )

    assert response.status_code == 400


def test_upload_rejects_an_empty_file(client):
    response = upload(client, create_report(client)["id"], "notes.txt", b"")

    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_upload_rejects_a_file_over_the_size_limit(client):
    response = upload(
        client,
        create_report(client)["id"],
        "notes.txt",
        b"x" * (MAX_UPLOAD_BYTES + 1),
    )

    assert response.status_code == 413


def test_upload_rejects_a_missing_filename(client):
    report = create_report(client)

    response = client.post(
        documents_url(report["id"]),
        files={"file": ("", io.BytesIO(b"Kickoff held."), "text/plain")},
    )

    assert response.status_code in (400, 422)


def test_upload_rejects_a_missing_file_part(client):
    response = client.post(documents_url(create_report(client)["id"]))

    assert response.status_code == 422


def test_upload_does_not_orphan_a_file_when_the_report_is_missing(client_and_db):
    client, _, uploads_dir = client_and_db

    upload(client, "missing", "notes.txt", b"Kickoff held.")

    assert list(uploads_dir.iterdir()) == []
