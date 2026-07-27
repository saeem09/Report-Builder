"""SQL for the report_sources and files tables.

report_sources is how uploaded documents accumulate across meetings. A progress
report is refreshed after every meeting, so each upload appends one row rather
than replacing anything, and generation reads all of them in upload order. The
parsed and cleaned text is stored alongside the file reference so generation
never re-parses a document it has already seen.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import repository
from .records import new_id, row_to_dict, rows_to_dicts, utc_now_iso

SOURCE_COLUMNS = (
    "id, report_id, file_id, original_name, cleaned_text, sort_order, created_at"
)
FILE_COLUMNS = "id, original_name, stored_path, content_type, created_at"


def _next_sort_order(conn: sqlite3.Connection, report_id: str) -> int:
    """Return the sort_order that appends a new source to the end."""
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order "
        "FROM report_sources WHERE report_id = ?",
        (report_id,),
    ).fetchone()
    return int(row["next_order"])


def add_source(
    conn: sqlite3.Connection,
    report_id: str,
    file_id: str,
    original_name: str,
    cleaned_text: str,
) -> Dict[str, Any]:
    """Append one uploaded document's cleaned text to a report."""
    repository.require_report(conn, report_id)
    source_id = new_id()
    conn.execute(
        "INSERT INTO report_sources (id, report_id, file_id, original_name, "
        "cleaned_text, sort_order, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            source_id,
            report_id,
            file_id,
            original_name,
            cleaned_text,
            _next_sort_order(conn, report_id),
            utc_now_iso(),
        ),
    )
    repository.touch_report(conn, report_id)
    row = conn.execute(
        "SELECT {0} FROM report_sources WHERE id = ?".format(SOURCE_COLUMNS),
        (source_id,),
    ).fetchone()
    return row_to_dict(row)


def list_sources(
    conn: sqlite3.Connection, report_id: str
) -> List[Dict[str, Any]]:
    """Return every source document for a report, oldest upload first."""
    rows = conn.execute(
        "SELECT {0} FROM report_sources WHERE report_id = ? "
        "ORDER BY sort_order ASC, id ASC".format(SOURCE_COLUMNS),
        (report_id,),
    ).fetchall()
    return rows_to_dicts(rows)


def record_file(
    conn: sqlite3.Connection,
    file_id: str,
    original_name: str,
    content_type: str,
) -> Dict[str, Any]:
    """Store metadata for a file already written to disk by app.storage.save_file.

    stored_path is informational only. Reads always go back through
    app.storage.read_file, which re-sanitizes the name itself, so this column
    is never used to build a filesystem path.
    """
    conn.execute(
        "INSERT OR REPLACE INTO files (id, original_name, stored_path, "
        "content_type, created_at) VALUES (?, ?, ?, ?, ?)",
        (
            file_id,
            original_name,
            "{0}/{1}".format(file_id, Path(original_name).name),
            content_type,
            utc_now_iso(),
        ),
    )
    return get_file_record(conn, file_id)


def get_file_record(
    conn: sqlite3.Connection, file_id: str
) -> Optional[Dict[str, Any]]:
    """Return one file's metadata, or None when the id is unknown."""
    row = conn.execute(
        "SELECT {0} FROM files WHERE id = ?".format(FILE_COLUMNS), (file_id,)
    ).fetchone()
    return row_to_dict(row)
