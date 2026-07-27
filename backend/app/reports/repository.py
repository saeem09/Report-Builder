"""SQL for the reports table.

Every function takes an already-open connection as its first argument and
never commits. Committing is the caller's job (see dependencies.open_db), so
one HTTP request is one atomic unit of work. No FastAPI type appears in this
module, which is what makes it testable with plain function calls.
"""

import sqlite3
from typing import Any, Dict, List

from .errors import ReportNotFoundError
from .records import new_id, row_to_dict, rows_to_dicts, utc_now_iso

REPORT_COLUMNS = "id, name, logo_file_id, created_at, updated_at"


def _not_found(report_id: str) -> ReportNotFoundError:
    return ReportNotFoundError("No report exists with id {0!r}.".format(report_id))


def create_report(conn: sqlite3.Connection, name: str) -> Dict[str, Any]:
    """Insert one report and return the stored row.

    created_at and updated_at start equal so a brand new report sorts to the
    top of the list endpoint.
    """
    report_id = new_id()
    timestamp = utc_now_iso()
    conn.execute(
        "INSERT INTO reports (id, name, logo_file_id, created_at, updated_at) "
        "VALUES (?, ?, NULL, ?, ?)",
        (report_id, name, timestamp, timestamp),
    )
    return get_report(conn, report_id)


def list_reports(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Return every report, most recently updated first.

    No filtering or pagination: Phase 6 owns the list UI and has not decided
    its filter needs, so building query parameters now would be speculative.
    id is the final tiebreak so the ordering is total and deterministic.
    """
    rows = conn.execute(
        "SELECT {0} FROM reports ORDER BY updated_at DESC, id DESC".format(
            REPORT_COLUMNS
        )
    ).fetchall()
    return rows_to_dicts(rows)


def get_report(conn: sqlite3.Connection, report_id: str) -> Dict[str, Any]:
    """Return one report or raise ReportNotFoundError."""
    row = conn.execute(
        "SELECT {0} FROM reports WHERE id = ?".format(REPORT_COLUMNS),
        (report_id,),
    ).fetchone()
    report = row_to_dict(row)
    if report is None:
        raise _not_found(report_id)
    return report


def report_exists(conn: sqlite3.Connection, report_id: str) -> bool:
    """Return whether a report id is present, without loading the row."""
    row = conn.execute("SELECT 1 FROM reports WHERE id = ?", (report_id,)).fetchone()
    return row is not None


def require_report(conn: sqlite3.Connection, report_id: str) -> None:
    """Raise ReportNotFoundError unless the report exists."""
    if not report_exists(conn, report_id):
        raise _not_found(report_id)


def rename_report(
    conn: sqlite3.Connection, report_id: str, name: str
) -> Dict[str, Any]:
    """Change a report's name and bump updated_at."""
    cursor = conn.execute(
        "UPDATE reports SET name = ?, updated_at = ? WHERE id = ?",
        (name, utc_now_iso(), report_id),
    )
    if cursor.rowcount == 0:
        raise _not_found(report_id)
    return get_report(conn, report_id)


def set_report_logo(
    conn: sqlite3.Connection, report_id: str, logo_file_id: str
) -> Dict[str, Any]:
    """Point a report at an uploaded logo file and bump updated_at."""
    cursor = conn.execute(
        "UPDATE reports SET logo_file_id = ?, updated_at = ? WHERE id = ?",
        (logo_file_id, utc_now_iso(), report_id),
    )
    if cursor.rowcount == 0:
        raise _not_found(report_id)
    return get_report(conn, report_id)


def touch_report(conn: sqlite3.Connection, report_id: str) -> None:
    """Bump updated_at only.

    Called whenever something owned by the report changes (a field, a source
    document, generated content) so the list endpoint's ordering reflects real
    activity rather than only renames.
    """
    cursor = conn.execute(
        "UPDATE reports SET updated_at = ? WHERE id = ?",
        (utc_now_iso(), report_id),
    )
    if cursor.rowcount == 0:
        raise _not_found(report_id)


def delete_report(conn: sqlite3.Connection, report_id: str) -> None:
    """Delete a report. Fields and source documents cascade via the schema FKs."""
    cursor = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    if cursor.rowcount == 0:
        raise _not_found(report_id)
