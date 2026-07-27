from pathlib import Path

import pytest

from app.db import init_db
from app.reports import fields, repository
from app.reports.dependencies import open_db
from app.reports.errors import (
    FieldNotFoundError,
    FieldOrderMismatchError,
    ReportNotFoundError,
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


def test_list_fields_is_empty_for_a_new_report(conn, report_id):
    assert fields.list_fields(conn, report_id) == []


def test_add_field_returns_a_full_row(conn, report_id):
    field = fields.add_field(conn, report_id, "Summary")

    assert field["report_id"] == report_id
    assert field["label"] == "Summary"
    assert field["content"] == ""
    assert field["sort_order"] == 0
    assert field["is_user_edited"] == 0
    assert field["id"]


def test_add_field_appends_to_the_end(conn, report_id):
    fields.add_field(conn, report_id, "Summary")
    second = fields.add_field(conn, report_id, "Blockers")

    assert second["sort_order"] == 1


def test_add_field_raises_for_an_unknown_report(conn):
    with pytest.raises(ReportNotFoundError):
        fields.add_field(conn, "missing", "Summary")


def test_add_field_bumps_the_report_timestamp(conn, report_id):
    before = repository.get_report(conn, report_id)["updated_at"]

    fields.add_field(conn, report_id, "Summary")

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_add_fields_creates_every_label_in_order(conn, report_id):
    created = fields.add_fields(conn, report_id, ["Summary", "Blockers", "Next"])

    assert [field["label"] for field in created] == ["Summary", "Blockers", "Next"]
    assert [field["sort_order"] for field in created] == [0, 1, 2]


def test_add_fields_with_no_labels_creates_nothing(conn, report_id):
    assert fields.add_fields(conn, report_id, []) == []
    assert fields.list_fields(conn, report_id) == []


def test_add_fields_raises_for_an_unknown_report(conn):
    with pytest.raises(ReportNotFoundError):
        fields.add_fields(conn, "missing", ["Summary"])


def test_list_fields_returns_sort_order_ascending(conn, report_id):
    fields.add_fields(conn, report_id, ["A", "B", "C"])

    labels = [field["label"] for field in fields.list_fields(conn, report_id)]

    assert labels == ["A", "B", "C"]


def test_list_fields_ignores_other_reports(conn, report_id):
    other_id = repository.create_report(conn, "Other")["id"]
    fields.add_field(conn, report_id, "Mine")
    fields.add_field(conn, other_id, "Theirs")

    labels = [field["label"] for field in fields.list_fields(conn, report_id)]

    assert labels == ["Mine"]


def test_get_field_returns_the_field(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")

    assert fields.get_field(conn, report_id, created["id"]) == created


def test_get_field_raises_for_an_unknown_field(conn, report_id):
    with pytest.raises(FieldNotFoundError):
        fields.get_field(conn, report_id, "missing")


def test_get_field_raises_when_the_field_belongs_to_another_report(conn, report_id):
    other_id = repository.create_report(conn, "Other")["id"]
    theirs = fields.add_field(conn, other_id, "Theirs")

    with pytest.raises(FieldNotFoundError):
        fields.get_field(conn, report_id, theirs["id"])


def test_reorder_fields_applies_the_given_order(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B", "C"])
    reversed_ids = [field["id"] for field in reversed(created)]

    reordered = fields.reorder_fields(conn, report_id, reversed_ids)

    assert [field["label"] for field in reordered] == ["C", "B", "A"]
    assert [field["sort_order"] for field in reordered] == [0, 1, 2]


def test_reorder_fields_persists_the_new_order(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])
    fields.reorder_fields(conn, report_id, [created[1]["id"], created[0]["id"]])

    labels = [field["label"] for field in fields.list_fields(conn, report_id)]

    assert labels == ["B", "A"]


def test_reorder_fields_bumps_the_report_timestamp(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])
    before = repository.get_report(conn, report_id)["updated_at"]

    fields.reorder_fields(conn, report_id, [created[1]["id"], created[0]["id"]])

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_reorder_fields_rejects_a_missing_id(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])

    with pytest.raises(FieldOrderMismatchError):
        fields.reorder_fields(conn, report_id, [created[0]["id"]])


def test_reorder_fields_rejects_an_unknown_id(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])

    with pytest.raises(FieldOrderMismatchError):
        fields.reorder_fields(
            conn, report_id, [created[0]["id"], created[1]["id"], "ghost"]
        )


def test_reorder_fields_rejects_a_duplicated_id(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])

    with pytest.raises(FieldOrderMismatchError):
        fields.reorder_fields(conn, report_id, [created[0]["id"], created[0]["id"]])


def test_reorder_fields_rejects_a_field_from_another_report(conn, report_id):
    mine = fields.add_field(conn, report_id, "Mine")
    other_id = repository.create_report(conn, "Other")["id"]
    theirs = fields.add_field(conn, other_id, "Theirs")

    with pytest.raises(FieldOrderMismatchError):
        fields.reorder_fields(conn, report_id, [theirs["id"], mine["id"]])


def test_reorder_fields_raises_for_an_unknown_report(conn):
    with pytest.raises(ReportNotFoundError):
        fields.reorder_fields(conn, "missing", [])


def test_update_field_content_marks_the_field_user_edited(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")

    updated = fields.update_field_content(
        conn, report_id, created["id"], "Hand written."
    )

    assert updated["content"] == "Hand written."
    assert updated["is_user_edited"] == 1


def test_update_field_content_bumps_the_report_timestamp(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")
    before = repository.get_report(conn, report_id)["updated_at"]

    fields.update_field_content(conn, report_id, created["id"], "Edited.")

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_update_field_content_accepts_an_empty_string(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")
    fields.update_field_content(conn, report_id, created["id"], "Draft.")

    updated = fields.update_field_content(conn, report_id, created["id"], "")

    assert updated["content"] == ""
    assert updated["is_user_edited"] == 1


def test_update_field_content_raises_for_an_unknown_field(conn, report_id):
    with pytest.raises(FieldNotFoundError):
        fields.update_field_content(conn, report_id, "missing", "text")


def test_update_field_content_raises_for_a_field_of_another_report(conn, report_id):
    other_id = repository.create_report(conn, "Other")["id"]
    theirs = fields.add_field(conn, other_id, "Theirs")

    with pytest.raises(FieldNotFoundError):
        fields.update_field_content(conn, report_id, theirs["id"], "text")


def test_set_generated_content_writes_without_marking_user_edited(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])

    fields.set_generated_content(
        conn, report_id, {created[0]["id"]: "draft a", created[1]["id"]: "draft b"}
    )

    stored = fields.list_fields(conn, report_id)
    assert [field["content"] for field in stored] == ["draft a", "draft b"]
    assert [field["is_user_edited"] for field in stored] == [0, 0]


def test_set_generated_content_with_nothing_to_write_is_a_no_op(conn, report_id):
    fields.add_field(conn, report_id, "A")

    fields.set_generated_content(conn, report_id, {})

    assert fields.list_fields(conn, report_id)[0]["content"] == ""


def test_set_generated_content_ignores_ids_from_another_report(conn, report_id):
    other_id = repository.create_report(conn, "Other")["id"]
    theirs = fields.add_field(conn, other_id, "Theirs")

    fields.set_generated_content(conn, report_id, {theirs["id"]: "leaked"})

    assert fields.get_field(conn, other_id, theirs["id"])["content"] == ""


def test_delete_field_removes_it(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")

    fields.delete_field(conn, report_id, created["id"])

    assert fields.list_fields(conn, report_id) == []


def test_delete_field_bumps_the_report_timestamp(conn, report_id):
    created = fields.add_field(conn, report_id, "Summary")
    before = repository.get_report(conn, report_id)["updated_at"]

    fields.delete_field(conn, report_id, created["id"])

    assert repository.get_report(conn, report_id)["updated_at"] > before


def test_delete_field_raises_for_an_unknown_field(conn, report_id):
    with pytest.raises(FieldNotFoundError):
        fields.delete_field(conn, report_id, "missing")


def test_delete_field_leaves_the_remaining_fields_in_order(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B", "C"])
    fields.delete_field(conn, report_id, created[1]["id"])

    remaining = fields.list_fields(conn, report_id)

    assert [field["label"] for field in remaining] == ["A", "C"]


def test_add_field_after_a_delete_does_not_reuse_a_sort_order(conn, report_id):
    created = fields.add_fields(conn, report_id, ["A", "B"])
    fields.delete_field(conn, report_id, created[1]["id"])

    appended = fields.add_field(conn, report_id, "C")

    assert appended["sort_order"] == 1
