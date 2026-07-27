"""Endpoints that combine storage, parsing, the LLM, and PDF rendering.

Kept separate from routes.py so neither file grows past the size the project
convention allows, and so the plain CRUD surface stays readable on its own.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from ..parsers import parse_document
from ..storage import read_file, save_file
from ..text_cleaning import clean_text
from . import fields as fields_repo
from . import generation, pdf_export, repository, sources
from .dependencies import get_db_path, get_uploads_dir, open_db
from .errors import PdfExportError
from .routes import build_report_detail
from .schemas import ReportDetailResponse, SourceDocumentResponse

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
ALLOWED_LOGO_CONTENT_TYPES = ("image/png", "image/jpeg", "image/gif", "image/webp")
UNSUPPORTED_LOGO_MESSAGE = (
    "The logo must be an image. Allowed types: {0}.".format(
        ", ".join(ALLOWED_LOGO_CONTENT_TYPES)
    )
)
MISSING_LOGO_FILE_MESSAGE = (
    "The report's logo file is missing from storage. Upload the logo again."
)


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


@router.post("/{report_id}/generate", response_model=ReportDetailResponse)
def generate_report(
    report_id: str, db_path: Path = Depends(get_db_path)
) -> Dict[str, Any]:
    """Draft content for every field the user has not edited.

    Exactly one Claude call is made per trigger, covering all draftable fields
    at once. A field the user has edited is neither sent nor overwritten, so
    re-triggering after a later meeting costs tokens only for the fields still
    untouched.
    """
    with open_db(db_path) as conn:
        generation.generate_report_content(conn, report_id)
        return build_report_detail(conn, report_id)


@router.put("/{report_id}/logo", response_model=ReportDetailResponse)
def upload_report_logo(
    report_id: str,
    file: UploadFile = File(...),
    db_path: Path = Depends(get_db_path),
    uploads_dir: Path = Depends(get_uploads_dir),
) -> Dict[str, Any]:
    """Set the company logo that appears on the exported PDF.

    PUT rather than POST because a report has at most one logo, so uploading
    again simply replaces it and the operation is idempotent. The content type
    is checked against an allowlist before anything is written; the previous
    logo file is left on disk rather than deleted, so an export that is
    mid-flight cannot lose its image.
    """
    original_name = _require_filename(file)
    content_type = file.content_type or DEFAULT_CONTENT_TYPE
    if content_type not in ALLOWED_LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=UNSUPPORTED_LOGO_MESSAGE,
        )
    content = read_upload(file)
    with open_db(db_path) as conn:
        repository.require_report(conn, report_id)
        file_id = save_file(content, original_name, uploads_dir=uploads_dir)
        sources.record_file(conn, file_id, original_name, content_type)
        repository.set_report_logo(conn, report_id, file_id)
        return build_report_detail(conn, report_id)


def _load_logo(conn, uploads_dir: Path, logo_file_id: Optional[str]):
    """Read a report's logo bytes, or return (None, None) when it has no logo.

    A logo id with no file behind it is reported as a PdfExportError rather
    than being ignored: silently exporting a logo-less PDF would hide real data
    loss from the user.
    """
    if not logo_file_id:
        return None, None
    record = sources.get_file_record(conn, logo_file_id)
    if record is None:
        raise PdfExportError(MISSING_LOGO_FILE_MESSAGE)
    try:
        logo_bytes = read_file(
            logo_file_id, record["original_name"], uploads_dir=uploads_dir
        )
    except OSError as error:
        raise PdfExportError(MISSING_LOGO_FILE_MESSAGE) from error
    return logo_bytes, record["content_type"]


@router.get("/{report_id}/export.pdf")
def export_report_pdf(
    report_id: str,
    db_path: Path = Depends(get_db_path),
    uploads_dir: Path = Depends(get_uploads_dir),
) -> Response:
    """Render a report to a downloadable PDF, logo included.

    Rendering is deterministic library work: no LLM call is made here, per the
    token-cost rules in AGENTS.md.
    """
    with open_db(db_path) as conn:
        report = repository.get_report(conn, report_id)
        report_fields = fields_repo.list_fields(conn, report_id)
        logo_bytes, logo_content_type = _load_logo(
            conn, uploads_dir, report["logo_file_id"]
        )
    pdf_bytes = pdf_export.render_report_pdf(
        report["name"], report_fields, logo_bytes, logo_content_type
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="{0}"'.format(
                pdf_export.build_pdf_filename(report["name"])
            )
        },
    )
