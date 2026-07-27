from pathlib import Path

import pytest

from app.db import init_db
from app.llm import LLMRequestError
from app.reports import fields, generation, repository, sources
from app.reports.dependencies import open_db
from app.reports.errors import NoSourceDocumentsError, ReportNotFoundError


class RecordingGenerator:
    """Stands in for app.llm.generate_report_fields. Never opens a socket."""

    def __init__(self, drafts=None, error=None):
        self._drafts = {} if drafts is None else drafts
        self._error = error
        self.calls = []

    def __call__(self, source_text, field_labels, client=None):
        self.calls.append((source_text, list(field_labels)))
        if self._error is not None:
            raise self._error
        return dict(
            (label, self._drafts.get(label, "")) for label in field_labels
        )


@pytest.fixture()
def conn(tmp_path: Path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with open_db(db_path) as connection:
        yield connection


@pytest.fixture()
def report_id(conn):
    return repository.create_report(conn, "Kickoff")["id"]


def install(monkeypatch, generator):
    monkeypatch.setattr(
        "app.reports.generation.generate_report_fields", generator
    )
    return generator


def test_build_source_text_labels_each_document(conn, report_id):
    sources.add_source(conn, report_id, "f1", "meeting-one.txt", "First meeting.")

    text = generation.build_source_text(sources.list_sources(conn, report_id))

    assert "Document: meeting-one.txt" in text
    assert "First meeting." in text


def test_build_source_text_joins_meetings_in_order(conn, report_id):
    sources.add_source(conn, report_id, "f1", "one.txt", "First meeting.")
    sources.add_source(conn, report_id, "f2", "two.txt", "Second meeting.")

    text = generation.build_source_text(sources.list_sources(conn, report_id))

    assert text.index("First meeting.") < text.index("Second meeting.")
    assert generation.SOURCE_SEPARATOR in text


def test_build_source_text_of_nothing_is_empty():
    assert generation.build_source_text([]) == ""


def test_generation_drafts_every_field(conn, report_id, monkeypatch):
    fields.add_fields(conn, report_id, ["Summary", "Blockers"])
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    install(
        monkeypatch,
        RecordingGenerator({"Summary": "Held.", "Blockers": "API blocked."}),
    )

    result = generation.generate_report_content(conn, report_id)

    assert [field["content"] for field in result] == ["Held.", "API blocked."]


def test_generation_makes_exactly_one_llm_call_for_many_fields(
    conn, report_id, monkeypatch
):
    fields.add_fields(conn, report_id, ["A", "B", "C", "D"])
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    generator = install(monkeypatch, RecordingGenerator())

    generation.generate_report_content(conn, report_id)

    assert len(generator.calls) == 1


def test_generation_sends_every_source_document_in_one_prompt(
    conn, report_id, monkeypatch
):
    fields.add_field(conn, report_id, "Summary")
    sources.add_source(conn, report_id, "f1", "one.txt", "First meeting.")
    sources.add_source(conn, report_id, "f2", "two.txt", "Second meeting.")
    generator = install(monkeypatch, RecordingGenerator())

    generation.generate_report_content(conn, report_id)

    source_text = generator.calls[0][0]
    assert "First meeting." in source_text
    assert "Second meeting." in source_text


def test_generation_skips_user_edited_fields(conn, report_id, monkeypatch):
    created = fields.add_fields(conn, report_id, ["Summary", "Blockers"])
    fields.update_field_content(conn, report_id, created[0]["id"], "My words.")
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    generator = install(
        monkeypatch,
        RecordingGenerator({"Summary": "OVERWRITTEN", "Blockers": "API blocked."}),
    )

    result = generation.generate_report_content(conn, report_id)

    assert generator.calls[0][1] == ["Blockers"]
    assert result[0]["content"] == "My words."
    assert result[0]["is_user_edited"] == 1
    assert result[1]["content"] == "API blocked."
    assert result[1]["is_user_edited"] == 0


def test_generation_makes_no_llm_call_when_every_field_is_user_edited(
    conn, report_id, monkeypatch
):
    created = fields.add_fields(conn, report_id, ["Summary"])
    fields.update_field_content(conn, report_id, created[0]["id"], "My words.")
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    generator = install(monkeypatch, RecordingGenerator())

    result = generation.generate_report_content(conn, report_id)

    assert generator.calls == []
    assert result[0]["content"] == "My words."


def test_generation_makes_no_llm_call_when_the_report_has_no_fields(
    conn, report_id, monkeypatch
):
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    generator = install(monkeypatch, RecordingGenerator())

    assert generation.generate_report_content(conn, report_id) == []
    assert generator.calls == []


def test_generation_raises_when_no_document_was_uploaded(
    conn, report_id, monkeypatch
):
    fields.add_field(conn, report_id, "Summary")
    generator = install(monkeypatch, RecordingGenerator())

    with pytest.raises(NoSourceDocumentsError):
        generation.generate_report_content(conn, report_id)

    assert generator.calls == []


def test_generation_raises_for_an_unknown_report(conn, monkeypatch):
    install(monkeypatch, RecordingGenerator())

    with pytest.raises(ReportNotFoundError):
        generation.generate_report_content(conn, "missing")


def test_generation_leaves_content_empty_for_a_label_claude_omitted(
    conn, report_id, monkeypatch
):
    fields.add_fields(conn, report_id, ["Summary", "Blockers"])
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    install(monkeypatch, RecordingGenerator({"Summary": "Held."}))

    result = generation.generate_report_content(conn, report_id)

    assert [field["content"] for field in result] == ["Held.", ""]


def test_generation_gives_two_fields_sharing_a_label_the_same_draft(
    conn, report_id, monkeypatch
):
    fields.add_fields(conn, report_id, ["Summary", "Summary"])
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    generator = install(monkeypatch, RecordingGenerator({"Summary": "Held."}))

    result = generation.generate_report_content(conn, report_id)

    assert generator.calls[0][1] == ["Summary", "Summary"]
    assert [field["content"] for field in result] == ["Held.", "Held."]


def test_generation_rerun_only_redrafts_untouched_fields(
    conn, report_id, monkeypatch
):
    created = fields.add_fields(conn, report_id, ["Summary", "Blockers"])
    sources.add_source(conn, report_id, "f1", "one.txt", "First meeting.")
    install(
        monkeypatch, RecordingGenerator({"Summary": "Draft 1", "Blockers": "None."})
    )
    generation.generate_report_content(conn, report_id)
    fields.update_field_content(conn, report_id, created[0]["id"], "My words.")
    sources.add_source(conn, report_id, "f2", "two.txt", "Second meeting.")
    generator = install(
        monkeypatch,
        RecordingGenerator({"Summary": "Draft 2", "Blockers": "API blocked."}),
    )

    result = generation.generate_report_content(conn, report_id)

    assert generator.calls[0][1] == ["Blockers"]
    assert result[0]["content"] == "My words."
    assert result[1]["content"] == "API blocked."


def test_generation_bumps_the_report_timestamp(conn, report_id, monkeypatch):
    fields.add_field(conn, report_id, "Summary")
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    before = repository.get_report(conn, report_id)["updated_at"]
    install(monkeypatch, RecordingGenerator({"Summary": "Held."}))

    generation.generate_report_content(conn, report_id)

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_generation_propagates_an_llm_failure(conn, report_id, monkeypatch):
    fields.add_field(conn, report_id, "Summary")
    sources.add_source(conn, report_id, "f1", "notes.txt", "Kickoff held.")
    install(monkeypatch, RecordingGenerator(error=LLMRequestError("upstream down")))

    with pytest.raises(LLMRequestError):
        generation.generate_report_content(conn, report_id)
