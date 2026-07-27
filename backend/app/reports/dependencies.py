"""How a route handler gets the resources it needs for one request.

The FastAPI dependencies here inject immutable path values, never live
handles. Tests swap them out with app.dependency_overrides so no test ever
reads or writes the real data/ directory.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..db import DB_PATH, get_connection
from ..storage import UPLOADS_DIR


def get_db_path() -> Path:
    """FastAPI dependency: the SQLite file the API reads and writes."""
    return DB_PATH


def get_uploads_dir() -> Path:
    """FastAPI dependency: the directory uploaded originals are stored in."""
    return UPLOADS_DIR


@contextmanager
def open_db(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Run one unit of work: commit on success, roll back on failure, always close.

    The connection is created here, inside the route handler's own call stack,
    rather than being yielded from a FastAPI dependency. sqlite3 connections
    default to check_same_thread=True, and FastAPI runs sync dependencies and
    sync route handlers on an anyio threadpool that does not guarantee the same
    worker for both. Creating and using the connection in one place removes
    that hazard by construction.
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
