"""SQL for the report_fields table.

update_field_content is the manual-edit path and is the only function here
that sets is_user_edited to 1. set_generated_content is the AI path and never
touches the flag. That split is what implements the "never regenerate a field
the user manually edited" rule from AGENTS.md.
"""

import sqlite3
from typing import Any, Dict, List

from . import repository
from .errors import FieldNotFoundError, FieldOrderMismatchError
from .records import new_id, row_to_dict, rows_to_dicts

FIELD_COLUMNS = "id, report_id, label, content, sort_order, is_user_edited"


def _field_not_found(field_id: str) -> FieldNotFoundError:
    return FieldNotFoundError(
        "No field exists with id {0!r} on this report.".format(field_id)
    )


def _next_sort_order(conn: sqlite3.Connection, report_id: str) -> int:
    """Return the sort_order that appends a new field to the end.

    COALESCE(MAX(...), -1) + 1 yields 0 for a report with no fields, and never
    reuses a value freed by a delete, so ordering stays stable.
    """
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order "
        "FROM report_fields WHERE report_id = ?",
        (report_id,),
    ).fetchone()
    return int(row["next_order"])


def list_fields(conn: sqlite3.Connection, report_id: str) -> List[Dict[str, Any]]:
    """Return one report's fields in display order."""
    rows = conn.execute(
        "SELECT {0} FROM report_fields WHERE report_id = ? "
        "ORDER BY sort_order ASC, id ASC".format(FIELD_COLUMNS),
        (report_id,),
    ).fetchall()
    return rows_to_dicts(rows)


def get_field(
    conn: sqlite3.Connection, report_id: str, field_id: str
) -> Dict[str, Any]:
    """Return one field or raise FieldNotFoundError.

    report_id is part of the lookup, not just a convenience: it stops a field
    id from one report being read or written through another report's URL.
    """
    row = conn.execute(
        "SELECT {0} FROM report_fields WHERE id = ? AND report_id = ?".format(
            FIELD_COLUMNS
        ),
        (field_id, report_id),
    ).fetchone()
    field = row_to_dict(row)
    if field is None:
        raise _field_not_found(field_id)
    return field


def add_field(
    conn: sqlite3.Connection, report_id: str, label: str
) -> Dict[str, Any]:
    """Append one empty field to a report."""
    repository.require_report(conn, report_id)
    field_id = new_id()
    conn.execute(
        "INSERT INTO report_fields (id, report_id, label, content, sort_order, "
        "is_user_edited) VALUES (?, ?, ?, '', ?, 0)",
        (field_id, report_id, label, _next_sort_order(conn, report_id)),
    )
    repository.touch_report(conn, report_id)
    return get_field(conn, report_id, field_id)


def add_fields(
    conn: sqlite3.Connection, report_id: str, labels: List[str]
) -> List[Dict[str, Any]]:
    """Append several fields at once, preserving the given label order."""
    repository.require_report(conn, report_id)
    return [add_field(conn, report_id, label) for label in labels]


def reorder_fields(
    conn: sqlite3.Connection, report_id: str, field_ids: List[str]
) -> List[Dict[str, Any]]:
    """Rewrite sort_order from a complete, ordered list of field ids.

    The request must name every field of this report exactly once. Anything
    else -- a missing id, an extra id, a duplicate, or an id belonging to
    another report -- is rejected as FieldOrderMismatchError rather than
    silently applying a partial order the user did not ask for.
    """
    repository.require_report(conn, report_id)
    existing_ids = [field["id"] for field in list_fields(conn, report_id)]
    if len(field_ids) != len(existing_ids) or set(field_ids) != set(existing_ids):
        raise FieldOrderMismatchError(
            "field_ids must list each of the {0} field(s) on this report "
            "exactly once.".format(len(existing_ids))
        )
    conn.executemany(
        "UPDATE report_fields SET sort_order = ? WHERE id = ? AND report_id = ?",
        [
            (position, field_id, report_id)
            for position, field_id in enumerate(field_ids)
        ],
    )
    repository.touch_report(conn, report_id)
    return list_fields(conn, report_id)


def update_field_content(
    conn: sqlite3.Connection, report_id: str, field_id: str, content: str
) -> Dict[str, Any]:
    """Store a manual edit and mark the field as user-edited from now on.

    Setting is_user_edited to 1 here is what stops the next generation run
    from spending tokens on this field and overwriting the user's words.
    """
    cursor = conn.execute(
        "UPDATE report_fields SET content = ?, is_user_edited = 1 "
        "WHERE id = ? AND report_id = ?",
        (content, field_id, report_id),
    )
    if cursor.rowcount == 0:
        raise _field_not_found(field_id)
    repository.touch_report(conn, report_id)
    return get_field(conn, report_id, field_id)


def set_generated_content(
    conn: sqlite3.Connection,
    report_id: str,
    content_by_field_id: Dict[str, str],
) -> None:
    """Write AI-drafted content without marking anything user-edited.

    The report_id guard in the WHERE clause means an id that does not belong
    to this report simply updates no rows.
    """
    if not content_by_field_id:
        return
    conn.executemany(
        "UPDATE report_fields SET content = ? WHERE id = ? AND report_id = ?",
        [
            (content, field_id, report_id)
            for field_id, content in content_by_field_id.items()
        ],
    )


def delete_field(conn: sqlite3.Connection, report_id: str, field_id: str) -> None:
    """Remove one field. Remaining sort_order values keep their relative order."""
    cursor = conn.execute(
        "DELETE FROM report_fields WHERE id = ? AND report_id = ?",
        (field_id, report_id),
    )
    if cursor.rowcount == 0:
        raise _field_not_found(field_id)
    repository.touch_report(conn, report_id)
