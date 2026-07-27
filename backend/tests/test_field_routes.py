from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides


@pytest.fixture()
def client(tmp_path: Path):
    test_client, _ = build_client(tmp_path)
    yield test_client
    reset_overrides()


@pytest.fixture()
def report(client):
    return create_report(client, "Kickoff", ["Summary", "Blockers"])


def fields_url(report_id: str) -> str:
    return "/api/reports/{0}/fields".format(report_id)


def field_url(report_id: str, field_id: str) -> str:
    return "/api/reports/{0}/fields/{1}".format(report_id, field_id)


def test_add_field_returns_201_and_appends_to_the_end(client, report):
    response = client.post(fields_url(report["id"]), json={"label": "Next steps"})

    assert response.status_code == 201
    body = response.json()
    assert body["label"] == "Next steps"
    assert body["sort_order"] == 2
    assert body["content"] == ""
    assert body["is_user_edited"] is False


def test_add_field_shows_up_on_the_report(client, report):
    client.post(fields_url(report["id"]), json={"label": "Next steps"})

    fetched = client.get("/api/reports/{0}".format(report["id"])).json()

    assert [field["label"] for field in fetched["fields"]] == [
        "Summary",
        "Blockers",
        "Next steps",
    ]


def test_add_field_trims_the_label(client, report):
    response = client.post(fields_url(report["id"]), json={"label": "  Risks  "})

    assert response.json()["label"] == "Risks"


def test_add_field_rejects_a_blank_label(client, report):
    response = client.post(fields_url(report["id"]), json={"label": "   "})

    assert response.status_code == 422


def test_add_field_returns_404_for_an_unknown_report(client):
    response = client.post(fields_url("missing"), json={"label": "Summary"})

    assert response.status_code == 404


def test_reorder_fields_applies_the_new_order(client, report):
    reversed_ids = [field["id"] for field in reversed(report["fields"])]

    response = client.put(
        "{0}/order".format(fields_url(report["id"])), json={"field_ids": reversed_ids}
    )

    assert response.status_code == 200
    assert [field["label"] for field in response.json()["fields"]] == [
        "Blockers",
        "Summary",
    ]


def test_reorder_fields_persists_across_requests(client, report):
    reversed_ids = [field["id"] for field in reversed(report["fields"])]
    client.put(
        "{0}/order".format(fields_url(report["id"])), json={"field_ids": reversed_ids}
    )

    fetched = client.get("/api/reports/{0}".format(report["id"])).json()

    assert [field["label"] for field in fetched["fields"]] == ["Blockers", "Summary"]
    assert [field["sort_order"] for field in fetched["fields"]] == [0, 1]


def test_reorder_fields_returns_400_for_an_incomplete_list(client, report):
    response = client.put(
        "{0}/order".format(fields_url(report["id"])),
        json={"field_ids": [report["fields"][0]["id"]]},
    )

    assert response.status_code == 400
    assert "exactly once" in response.json()["detail"]


def test_reorder_fields_returns_400_for_an_unknown_field_id(client, report):
    response = client.put(
        "{0}/order".format(fields_url(report["id"])),
        json={"field_ids": [report["fields"][0]["id"], "ghost"]},
    )

    assert response.status_code == 400


def test_reorder_fields_returns_422_for_an_empty_list(client, report):
    response = client.put(
        "{0}/order".format(fields_url(report["id"])), json={"field_ids": []}
    )

    assert response.status_code == 422


def test_reorder_fields_returns_404_for_an_unknown_report(client, report):
    response = client.put(
        "{0}/order".format(fields_url("missing")),
        json={"field_ids": [report["fields"][0]["id"]]},
    )

    assert response.status_code == 404


def test_update_field_content_marks_it_user_edited(client, report):
    field_id = report["fields"][0]["id"]

    response = client.patch(
        field_url(report["id"], field_id), json={"content": "Hand written."}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["content"] == "Hand written."
    assert body["is_user_edited"] is True


def test_update_field_content_accepts_an_empty_string(client, report):
    field_id = report["fields"][0]["id"]
    client.patch(field_url(report["id"], field_id), json={"content": "Draft."})

    response = client.patch(field_url(report["id"], field_id), json={"content": ""})

    assert response.status_code == 200
    assert response.json()["content"] == ""
    assert response.json()["is_user_edited"] is True


def test_update_field_content_returns_404_for_an_unknown_field(client, report):
    response = client.patch(
        field_url(report["id"], "missing"), json={"content": "text"}
    )

    assert response.status_code == 404


def test_update_field_content_returns_404_for_a_field_of_another_report(client, report):
    other = create_report(client, "Other", ["Theirs"])

    response = client.patch(
        field_url(report["id"], other["fields"][0]["id"]), json={"content": "text"}
    )

    assert response.status_code == 404


def test_update_field_content_rejects_a_missing_content_key(client, report):
    response = client.patch(field_url(report["id"], report["fields"][0]["id"]), json={})

    assert response.status_code == 422


def test_delete_field_returns_204_and_removes_it(client, report):
    field_id = report["fields"][0]["id"]

    response = client.delete(field_url(report["id"], field_id))

    assert response.status_code == 204
    assert response.content == b""
    fetched = client.get("/api/reports/{0}".format(report["id"])).json()
    assert [field["label"] for field in fetched["fields"]] == ["Blockers"]


def test_delete_field_returns_404_for_an_unknown_field(client, report):
    assert client.delete(field_url(report["id"], "missing")).status_code == 404


def test_delete_field_returns_404_for_a_field_of_another_report(client, report):
    other = create_report(client, "Other", ["Theirs"])

    response = client.delete(field_url(report["id"], other["fields"][0]["id"]))

    assert response.status_code == 404
