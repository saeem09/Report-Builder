"""Endpoints that combine storage, parsing, the LLM, and PDF rendering.

Kept separate from routes.py so neither file grows past the size the project
convention allows, and so the plain CRUD surface stays readable on its own.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ..parsers import parse_document
from ..storage import save_file
from ..text_cleaning import clean_text
from . import repository, sources
from .dependencies import get_db_path, get_uploads_dir, open_db
from .schemas import SourceDocumentResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
EMPTY_UPLOAD_MESSAGE = "The uploaded file is empty."
MISSING_FILENAME_MESSAGE = (
    "The uploaded file has no name, so its type cannot be determined."
)
TOO_LARGE_MESSAGE = "The uploaded file exceeds the {0} byte limit.".format(
    MAX_UPLOAD_BYTES
)
DEFAULT_CONTENT_TYPE = "application/octet-stream"


def read_upload(file: UploadFile) -> bytes:
    """Read an uploaded file, rejecting empty and over-sized payloads.

    Exactly one byte past the limit is read, so an over-sized upload is
    detected without ever holding more than the limit plus one byte in memory
    and without trusting a client-supplied Content-Length header.
    """
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=TOO_LARGE_MESSAGE,
        )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=EMPTY_UPLOAD_MESSAGE
        )
    return content


def _require_filename(file: UploadFile) -> str:
    """Return the upload's filename, rejecting a missing or blank one."""
    original_name = (file.filename or "").strip()
    if not original_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=MISSING_FILENAME_MESSAGE
        )
    return original_name


@router.post(
    "/{report_id}/documents",
    status_code=status.HTTP_201_CREATED,
    response_model=SourceDocumentResponse,
)
def upload_source_document(
    report_id: str,
    file: UploadFile = File(...),
    db_path: Path = Depends(get_db_path),
    uploads_dir: Path = Depends(get_uploads_dir),
) -> Dict[str, Any]:
    """Attach one meeting's document to a report.

    The document is parsed and cleaned before anything is written, so a bad
    file is rejected without leaving a row or a file behind. The report's
    existence is checked before the file is saved for the same reason.
    parse_document raises DocumentParseError (or UnsupportedFileTypeError,
    which subclasses it) and the registered handler turns that into a 400.
    """
    original_name = _require_filename(file)
    content = read_upload(file)
    cleaned_text = clean_text(parse_document(content, original_name))
    content_type = file.content_type or DEFAULT_CONTENT_TYPE
    with open_db(db_path) as conn:
        repository.require_report(conn, report_id)
        file_id = save_file(content, original_name, uploads_dir=uploads_dir)
        sources.record_file(conn, file_id, original_name, content_type)
        return sources.add_source(
            conn, report_id, file_id, original_name, cleaned_text
        )
