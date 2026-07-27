"""Small shared helpers for turning database rows into API-safe values.

sqlite3.Row is not JSON-serializable and is a driver type, so it never leaves
the repository layer. Every repository function returns plain dicts built
here.
"""

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

UTC_SUFFIX = "Z"
ISO_OFFSET_SUFFIX = "+00:00"


def new_id() -> str:
    """Return a fresh primary key. Random ids keep inserts collision-free."""
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    """Return the current UTC time as a sortable ISO 8601 string.

    Microseconds are kept deliberately. created_at and updated_at are stored as
    text and ordered lexicographically, so second-resolution timestamps would
    make list ordering ambiguous whenever two rows are written inside the same
    second, which is exactly what a fast test suite does.
    """
    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace(ISO_OFFSET_SUFFIX, UTC_SUFFIX)
    )


def row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Copy one row into a new plain dict. None passes straight through."""
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Copy every row into a new list of plain dicts."""
    return [dict(row) for row in rows]
