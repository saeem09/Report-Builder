from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides

from app.reports.schemas import MAX_FIELDS_PER_REPORT, MAX_NAME_LENGTH


@pytest.fixture()
def client(tmp_path: Path):
    test_client, _ = build_client(tmp_path)
    yield test_client
    reset_overrides()


def test_create_report_returns_201_with_an_empty_field_list(client):
    response = client.post("/api/reports", json={"name": "Kickoff"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Kickoff"
    assert body["logo_file_id"] is None
    assert body["fields"] == []
    assert body["created_at"] == body["updated_at"]


def test_create_report_creates_the_requested_fields_in_order(client):
    body = create_report(client, "Kickoff", ["Summary", "Blockers"])

    assert [field["label"] for field in body["fields"]] == ["Summary", "Blockers"]
    assert [field["sort_order"] for field in body["fields"]] == [0, 1]
    assert [field["is_user_edited"] for field in body["fields"]] == [False, False]


def test_create_report_trims_surrounding_whitespace_from_the_name(client):
    body = create_report(client, "  Kickoff  ")

    assert body["name"] == "Kickoff"


def test_create_report_rejects_a_blank_name(client):
    response = client.post("/api/reports", json={"name": "   "})

    assert response.status_code == 422
    assert "must not be blank" in response.json()["detail"][0]["msg"]


def test_create_report_rejects_a_missing_name(client):
    assert client.post("/api/reports", json={}).status_code == 422


def test_create_report_rejects_an_over_long_name(client):
    response = client.post("/api/reports", json={"name": "x" * (MAX_NAME_LENGTH + 1)})

    assert response.status_code == 422


def test_create_report_rejects_too_many_field_labels(client):
    response = client.post(
        "/api/reports",
        json={"name": "Kickoff", "field_labels": ["L"] * (MAX_FIELDS_PER_REPORT + 1)},
    )

    assert response.status_code == 422


def test_create_report_rejects_a_blank_field_label(client):
    response = client.post(
        "/api/reports", json={"name": "Kickoff", "field_labels": ["Summary", "  "]}
    )

    assert response.status_code == 422


def test_list_reports_is_empty_initially(client):
    response = client.get("/api/reports")

    assert response.status_code == 200
    assert response.json() == {"reports": []}


def test_list_reports_returns_most_recently_updated_first(client):
    create_report(client, "First")
    create_report(client, "Second")

    names = [report["name"] for report in client.get("/api/reports").json()["reports"]]

    assert names == ["Second", "First"]


def test_list_reports_does_not_include_fields(client):
    create_report(client, "Kickoff", ["Summary"])

    report = client.get("/api/reports").json()["reports"][0]

    assert "fields" not in report


def test_get_report_returns_its_fields_in_sort_order(client):
    created = create_report(client, "Kickoff", ["Summary", "Blockers"])

    response = client.get("/api/reports/{0}".format(created["id"]))

    assert response.status_code == 200
    assert [field["label"] for field in response.json()["fields"]] == [
        "Summary",
        "Blockers",
    ]


def test_get_report_returns_404_for_an_unknown_id(client):
    response = client.get("/api/reports/missing")

    assert response.status_code == 404
    assert "missing" in response.json()["detail"]


def test_rename_report_updates_the_name_and_timestamp(client):
    created = create_report(client, "Kickoff")

    response = client.patch(
        "/api/reports/{0}".format(created["id"]), json={"name": "Kickoff v2"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Kickoff v2"
    assert body["updated_at"] > created["updated_at"]


def test_rename_report_persists_across_requests(client):
    created = create_report(client, "Kickoff")
    client.patch("/api/reports/{0}".format(created["id"]), json={"name": "Renamed"})

    fetched = client.get("/api/reports/{0}".format(created["id"]))

    assert fetched.json()["name"] == "Renamed"


def test_rename_report_keeps_its_fields(client):
    created = create_report(client, "Kickoff", ["Summary"])

    response = client.patch(
        "/api/reports/{0}".format(created["id"]), json={"name": "Renamed"}
    )

    assert [field["label"] for field in response.json()["fields"]] == ["Summary"]


def test_rename_report_returns_404_for_an_unknown_id(client):
    response = client.patch("/api/reports/missing", json={"name": "X"})

    assert response.status_code == 404


def test_rename_report_rejects_a_blank_name(client):
    created = create_report(client, "Kickoff")

    response = client.patch(
        "/api/reports/{0}".format(created["id"]), json={"name": ""}
    )

    assert response.status_code == 422


def test_delete_report_returns_204_and_removes_it(client):
    created = create_report(client, "Kickoff")

    response = client.delete("/api/reports/{0}".format(created["id"]))

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/reports/{0}".format(created["id"])).status_code == 404


def test_delete_report_returns_404_for_an_unknown_id(client):
    assert client.delete("/api/reports/missing").status_code == 404


def test_full_create_read_update_delete_cycle(client):
    created = create_report(client, "Kickoff", ["Summary"])
    report_id = created["id"]

    assert client.get("/api/reports/{0}".format(report_id)).status_code == 200
    assert (
        client.patch(
            "/api/reports/{0}".format(report_id), json={"name": "Kickoff v2"}
        ).status_code
        == 200
    )
    assert client.get("/api/reports/{0}".format(report_id)).json()["name"] == (
        "Kickoff v2"
    )
    assert client.delete("/api/reports/{0}".format(report_id)).status_code == 204
    assert client.get("/api/reports").json() == {"reports": []}


def test_tests_do_not_touch_the_real_application_database(client, tmp_path):
    from app.db import DB_PATH

    create_report(client, "Kickoff")

    assert (tmp_path / "test.db").exists()
    assert not DB_PATH.exists()
