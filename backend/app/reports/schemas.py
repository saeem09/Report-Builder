"""Request and response models for the progress report API.

These are the system boundary: every JSON body is validated here before any
route handler or SQL sees it. Length caps exist so a single request cannot
push an unbounded string into SQLite or into an LLM prompt.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

MAX_NAME_LENGTH = 200
MAX_LABEL_LENGTH = 200
MAX_CONTENT_LENGTH = 50000
MAX_FIELDS_PER_REPORT = 100
MAX_FIELD_ID_LENGTH = 64


def _require_non_blank(value: str) -> str:
    """Reject whitespace-only text and return the trimmed value.

    min_length alone would accept "   ", which is not a usable report name or
    field label. Returning the trimmed value means storage never holds
    accidental padding.
    """
    trimmed = value.strip()
    if not trimmed:
        raise ValueError("must not be blank")
    return trimmed


class ReportCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    field_labels: List[str] = Field(
        default_factory=list, max_length=MAX_FIELDS_PER_REPORT
    )

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _require_non_blank(value)

    @field_validator("field_labels")
    @classmethod
    def _check_labels(cls, value: List[str]) -> List[str]:
        return [_require_non_blank(label)[:MAX_LABEL_LENGTH] for label in value]


class ReportRenameRequest(BaseModel):
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def _check_name(cls, value: str) -> str:
        return _require_non_blank(value)


class FieldCreateRequest(BaseModel):
    label: str = Field(min_length=1, max_length=MAX_LABEL_LENGTH)

    @field_validator("label")
    @classmethod
    def _check_label(cls, value: str) -> str:
        return _require_non_blank(value)


class FieldContentRequest(BaseModel):
    """A manual edit. Blank content is allowed: clearing a field is legitimate."""

    content: str = Field(max_length=MAX_CONTENT_LENGTH)


class FieldOrderRequest(BaseModel):
    field_ids: List[str] = Field(min_length=1, max_length=MAX_FIELDS_PER_REPORT)

    @field_validator("field_ids")
    @classmethod
    def _check_ids(cls, value: List[str]) -> List[str]:
        return [_require_non_blank(field_id)[:MAX_FIELD_ID_LENGTH] for field_id in value]


class FieldResponse(BaseModel):
    id: str
    report_id: str
    label: str
    content: str
    sort_order: int
    is_user_edited: bool


class ReportSummaryResponse(BaseModel):
    id: str
    name: str
    logo_file_id: Optional[str] = None
    created_at: str
    updated_at: str


class ReportDetailResponse(ReportSummaryResponse):
    fields: List[FieldResponse]


class ReportListResponse(BaseModel):
    reports: List[ReportSummaryResponse]


class SourceDocumentResponse(BaseModel):
    id: str
    report_id: str
    file_id: str
    original_name: str
    sort_order: int
    created_at: str
