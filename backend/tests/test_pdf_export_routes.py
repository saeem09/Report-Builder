import base64
import io
from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture()
def client_and_db(tmp_path: Path):
    test_client, db_path = build_client(tmp_path)
    yield test_client, db_path, tmp_path / "uploads"
    reset_overrides()


@pytest.fixture()
def client(client_and_db):
    return client_and_db[0]


def export_url(report_id: str) -> str:
    return "/api/reports/{0}/export.pdf".format(report_id)


def test_export_returns_pdf_bytes(client):
    report = create_report(client, "Kickoff", ["Summary"])

    response = client.get(export_url(report["id"]))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_export_sets_a_slugified_attachment_filename(client):
    report = create_report(client, "Q3 Kickoff Review")

    response = client.get(export_url(report["id"]))

    assert response.headers["content-disposition"] == (
        'attachment; filename="Q3-Kickoff-Review.pdf"'
    )


def test_export_includes_the_logo_when_one_is_set(client):
    report = create_report(client, "Kickoff", ["Summary"])
    without_logo = client.get(export_url(report["id"])).content
    client.put(
        "/api/reports/{0}/logo".format(report["id"]),
        files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
    )

    with_logo = client.get(export_url(report["id"])).content

    assert len(with_logo) > len(without_logo)


def test_export_returns_404_for_an_unknown_report(client):
    assert client.get(export_url("missing")).status_code == 404


def test_export_works_for_a_report_with_no_fields(client):
    report = create_report(client, "Kickoff")

    assert client.get(export_url(report["id"])).content.startswith(b"%PDF-")


def test_export_returns_500_when_the_logo_file_is_missing_from_disk(client_and_db):
    client, _, uploads_dir = client_and_db
    report = create_report(client, "Kickoff")
    file_id = client.put(
        "/api/reports/{0}/logo".format(report["id"]),
        files={"file": ("logo.png", io.BytesIO(PNG_BYTES), "image/png")},
    ).json()["logo_file_id"]
    (uploads_dir / file_id / "logo.png").unlink()

    response = client.get(export_url(report["id"]))

    assert response.status_code == 500
    assert "logo" in response.json()["detail"].lower()
