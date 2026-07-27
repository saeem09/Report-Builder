"""Report and field HTTP endpoints.

Handlers stay thin on purpose: validate with Pydantic, open one connection for
the unit of work, call the repository, return. Missing rows and bad reorder
requests raise domain errors that exception_handlers turns into responses, so
there is no per-route 404 boilerplate.
"""

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, Response, status

from . import fields as fields_repo
from . import repository
from .dependencies import get_db_path, open_db
from .schemas import (
    FieldContentRequest,
    FieldCreateRequest,
    FieldOrderRequest,
    FieldResponse,
    ReportCreateRequest,
    ReportDetailResponse,
    ReportListResponse,
    ReportRenameRequest,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])


def build_report_detail(conn, report_id: str) -> Dict[str, Any]:
    """Assemble the ReportDetail payload: the report plus its ordered fields.

    A new dict is built rather than mutating the repository's row, so the
    repository result is never modified in place.
    """
    report = repository.get_report(conn, report_id)
    return dict(report, fields=fields_repo.list_fields(conn, report_id))


@router.post(
    "", status_code=status.HTTP_201_CREATED, response_model=ReportDetailResponse
)
def create_report(
    payload: ReportCreateRequest, db_path: Path = Depends(get_db_path)
) -> Dict[str, Any]:
    """Create a report, optionally with its initial field labels."""
    with open_db(db_path) as conn:
        report = repository.create_report(conn, payload.name)
        fields_repo.add_fields(conn, report["id"], payload.field_labels)
        return build_report_detail(conn, report["id"])


@router.get("", response_model=ReportListResponse)
def list_reports(db_path: Path = Depends(get_db_path)) -> Dict[str, Any]:
    """Return every report, most recently updated first.

    Fields are deliberately omitted: the list page shows names and dates, and
    loading every field of every report would be wasted work.
    """
    with open_db(db_path) as conn:
        return {"reports": repository.list_reports(conn)}


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report(
    report_id: str, db_path: Path = Depends(get_db_path)
) -> Dict[str, Any]:
    """Return one report with its fields in sort_order."""
    with open_db(db_path) as conn:
        return build_report_detail(conn, report_id)


@router.patch("/{report_id}", response_model=ReportDetailResponse)
def rename_report(
    report_id: str,
    payload: ReportRenameRequest,
    db_path: Path = Depends(get_db_path),
) -> Dict[str, Any]:
    """Rename a report."""
    with open_db(db_path) as conn:
        repository.rename_report(conn, report_id, payload.name)
        return build_report_detail(conn, report_id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str, db_path: Path = Depends(get_db_path)) -> Response:
    """Delete a report. Its fields and source documents cascade away with it."""
    with open_db(db_path) as conn:
        repository.delete_report(conn, report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{report_id}/fields",
    status_code=status.HTTP_201_CREATED,
    response_model=FieldResponse,
)
def add_field(
    report_id: str,
    payload: FieldCreateRequest,
    db_path: Path = Depends(get_db_path),
) -> Dict[str, Any]:
    """Append one empty field to a report."""
    with open_db(db_path) as conn:
        return fields_repo.add_field(conn, report_id, payload.label)


@router.put("/{report_id}/fields/order", response_model=ReportDetailResponse)
def reorder_fields(
    report_id: str,
    payload: FieldOrderRequest,
    db_path: Path = Depends(get_db_path),
) -> Dict[str, Any]:
    """Persist a drag-and-drop reorder.

    The client sends the complete field id list in its new order. Sending the
    whole list rather than a single moved id makes the request idempotent and
    lets the server reject any order that does not match the report exactly.
    """
    with open_db(db_path) as conn:
        fields_repo.reorder_fields(conn, report_id, payload.field_ids)
        return build_report_detail(conn, report_id)


@router.patch("/{report_id}/fields/{field_id}", response_model=FieldResponse)
def update_field_content(
    report_id: str,
    field_id: str,
    payload: FieldContentRequest,
    db_path: Path = Depends(get_db_path),
) -> Dict[str, Any]:
    """Save a manual edit.

    This is the only endpoint that sets is_user_edited, which is what stops
    the generation endpoint from ever overwriting the user's own words.
    """
    with open_db(db_path) as conn:
        return fields_repo.update_field_content(
            conn, report_id, field_id, payload.content
        )


@router.delete(
    "/{report_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_field(
    report_id: str, field_id: str, db_path: Path = Depends(get_db_path)
) -> Response:
    """Remove one field from a report."""
    with open_db(db_path) as conn:
        fields_repo.delete_field(conn, report_id, field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
