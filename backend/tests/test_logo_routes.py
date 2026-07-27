import io
from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides

from app.db import get_connection

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture()
def client_and_db(tmp_path: Path):
    test_client, db_path = build_client(tmp_path)
    yield test_client, db_path, tmp_path / "uploads"
    reset_overrides()


@pytest.fixture()
def client(client_and_db):
    return client_and_db[0]


def logo_url(report_id: str) -> str:
    return "/api/reports/{0}/logo".format(report_id)


def put_logo(client, report_id, name="logo.png", content=PNG_BYTES, ctype="image/png"):
    return client.put(
        logo_url(report_id), files={"file": (name, io.BytesIO(content), ctype)}
    )


def test_upload_logo_sets_the_logo_file_id(client):
    report = create_report(client)

    response = put_logo(client, report["id"])

    assert response.status_code == 200
    assert response.json()["logo_file_id"]


def test_upload_logo_persists_across_requests(client):
    report = create_report(client)
    file_id = put_logo(client, report["id"]).json()["logo_file_id"]

    fetched = client.get("/api/reports/{0}".format(report["id"])).json()

    assert fetched["logo_file_id"] == file_id


def test_upload_logo_returns_the_full_report_detail(client):
    report = create_report(client, "Kickoff", ["Summary"])

    body = put_logo(client, report["id"]).json()

    assert body["name"] == "Kickoff"
    assert [field["label"] for field in body["fields"]] == ["Summary"]


def test_upload_logo_saves_the_image_to_the_uploads_directory(client_and_db):
    client, _, uploads_dir = client_and_db
    report = create_report(client)

    file_id = put_logo(client, report["id"]).json()["logo_file_id"]

    assert (uploads_dir / file_id / "logo.png").read_bytes() == PNG_BYTES


def test_upload_logo_records_the_file_metadata(client_and_db):
    client, db_path, _ = client_and_db
    report = create_report(client)
    file_id = put_logo(client, report["id"]).json()["logo_file_id"]

    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT original_name, content_type FROM files WHERE id = ?", (file_id,)
        ).fetchone()
    finally:
        conn.close()

    assert row["original_name"] == "logo.png"
    assert row["content_type"] == "image/png"


def test_uploading_a_second_logo_replaces_the_first(client):
    report = create_report(client)
    first = put_logo(client, report["id"]).json()["logo_file_id"]

    second = put_logo(client, report["id"], "other.png").json()["logo_file_id"]

    assert second != first
    fetched = client.get("/api/reports/{0}".format(report["id"])).json()
    assert fetched["logo_file_id"] == second


def test_upload_logo_bumps_the_report_timestamp(client):
    report = create_report(client)

    body = put_logo(client, report["id"]).json()

    assert body["updated_at"] > report["updated_at"]


@pytest.mark.parametrize(
    "name,content_type",
    [
        ("logo.jpg", "image/jpeg"),
        ("logo.gif", "image/gif"),
        ("logo.webp", "image/webp"),
    ],
)
def test_upload_logo_accepts_the_other_allowed_image_types(client, name, content_type):
    report = create_report(client)

    response = put_logo(client, report["id"], name, b"fake image bytes", content_type)

    assert response.status_code == 200


def test_upload_logo_rejects_a_non_image_content_type(client):
    report = create_report(client)

    response = put_logo(client, report["id"], "notes.txt", b"text", "text/plain")

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()


def test_upload_logo_rejects_an_empty_file(client):
    report = create_report(client)

    response = put_logo(client, report["id"], "logo.png", b"", "image/png")

    assert response.status_code == 400


def test_upload_logo_returns_404_for_an_unknown_report(client):
    assert put_logo(client, "missing").status_code == 404


def test_upload_logo_does_not_orphan_a_file_for_an_unknown_report(client_and_db):
    client, _, uploads_dir = client_and_db

    put_logo(client, "missing")

    assert list(uploads_dir.iterdir()) == []


def test_upload_logo_rejects_a_missing_file_part(client):
    assert client.put(logo_url(create_report(client)["id"])).status_code == 422
