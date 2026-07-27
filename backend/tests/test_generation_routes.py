import io
from pathlib import Path

import pytest
from api_helpers import build_client, create_report, reset_overrides

from app.llm import LLMRequestError


@pytest.fixture()
def client(tmp_path: Path):
    test_client, _ = build_client(tmp_path)
    yield test_client
    reset_overrides()


def generate_url(report_id: str) -> str:
    return "/api/reports/{0}/generate".format(report_id)


def upload(client, report_id, name="notes.txt", content=b"Kickoff held."):
    return client.post(
        "/api/reports/{0}/documents".format(report_id),
        files={"file": (name, io.BytesIO(content), "text/plain")},
    )


def install(monkeypatch, drafts=None, error=None):
    calls = []

    def fake_generate(source_text, field_labels, client=None):
        calls.append((source_text, list(field_labels)))
        if error is not None:
            raise error
        return dict(
            (label, (drafts or {}).get(label, "")) for label in field_labels
        )

    monkeypatch.setattr(
        "app.reports.generation.generate_report_fields", fake_generate
    )
    return calls


def test_generate_returns_the_report_with_drafted_content(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary", "Blockers"])
    upload(client, report["id"])
    install(monkeypatch, {"Summary": "Held.", "Blockers": "API blocked."})

    response = client.post(generate_url(report["id"]))

    assert response.status_code == 200
    body = response.json()
    assert [field["content"] for field in body["fields"]] == [
        "Held.",
        "API blocked.",
    ]
    assert [field["is_user_edited"] for field in body["fields"]] == [False, False]


def test_generate_makes_exactly_one_llm_call(client, monkeypatch):
    report = create_report(client, "Kickoff", ["A", "B", "C"])
    upload(client, report["id"])
    calls = install(monkeypatch)

    client.post(generate_url(report["id"]))

    assert len(calls) == 1


def test_generate_does_not_overwrite_a_user_edited_field(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary", "Blockers"])
    upload(client, report["id"])
    client.patch(
        "/api/reports/{0}/fields/{1}".format(
            report["id"], report["fields"][0]["id"]
        ),
        json={"content": "My words."},
    )
    calls = install(monkeypatch, {"Summary": "OVERWRITTEN", "Blockers": "None."})

    body = client.post(generate_url(report["id"])).json()

    assert calls[0][1] == ["Blockers"]
    assert body["fields"][0]["content"] == "My words."
    assert body["fields"][0]["is_user_edited"] is True


def test_generate_persists_the_drafts(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    upload(client, report["id"])
    install(monkeypatch, {"Summary": "Held."})
    client.post(generate_url(report["id"]))

    fetched = client.get("/api/reports/{0}".format(report["id"])).json()

    assert fetched["fields"][0]["content"] == "Held."


def test_generate_uses_every_uploaded_meeting(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    upload(client, report["id"], "one.txt", b"First meeting.")
    upload(client, report["id"], "two.txt", b"Second meeting.")
    calls = install(monkeypatch, {"Summary": "Both."})

    client.post(generate_url(report["id"]))

    assert "First meeting." in calls[0][0]
    assert "Second meeting." in calls[0][0]


def test_generate_returns_409_without_any_source_document(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    calls = install(monkeypatch)

    response = client.post(generate_url(report["id"]))

    assert response.status_code == 409
    assert "upload" in response.json()["detail"].lower()
    assert calls == []


def test_generate_returns_404_for_an_unknown_report(client, monkeypatch):
    install(monkeypatch)

    assert client.post(generate_url("missing")).status_code == 404


def test_generate_returns_502_when_the_llm_fails(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    upload(client, report["id"])
    install(monkeypatch, error=LLMRequestError("The request to Claude failed"))

    response = client.post(generate_url(report["id"]))

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "The AI service could not draft this report. Please try again."
    )


def test_generate_does_not_leak_the_upstream_error_text(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    upload(client, report["id"])
    install(monkeypatch, error=LLMRequestError("secret upstream detail"))

    response = client.post(generate_url(report["id"]))

    assert "secret upstream detail" not in response.text


def test_generate_leaves_content_untouched_when_the_llm_fails(client, monkeypatch):
    report = create_report(client, "Kickoff", ["Summary"])
    upload(client, report["id"])
    install(monkeypatch, {"Summary": "Held."})
    client.post(generate_url(report["id"]))
    install(monkeypatch, error=LLMRequestError("down"))

    client.post(generate_url(report["id"]))
    fetched = client.get("/api/reports/{0}".format(report["id"])).json()

    assert fetched["fields"][0]["content"] == "Held."
