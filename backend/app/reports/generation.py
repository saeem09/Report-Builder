"""The one place the backend asks Claude to draft report content.

Two token-cost rules from AGENTS.md are enforced here, not in the route layer:
every field of one report is drafted in a single batched call, and a field the
user has edited is never sent and never overwritten.
"""

import sqlite3
from typing import Any, Dict, List

from ..llm import generate_report_fields
from . import fields as fields_repo
from . import repository, sources
from .errors import NoSourceDocumentsError

SOURCE_SEPARATOR = "\n\n---\n\n"
DOCUMENT_HEADING_TEMPLATE = "Document: {0}"
NO_SOURCES_MESSAGE = (
    "This report has no source documents yet. Upload a document before "
    "generating content."
)


def build_source_text(source_rows: List[Dict[str, Any]]) -> str:
    """Join every uploaded document into one prompt body, oldest meeting first.

    Each block is headed with the original filename so Claude can attribute a
    statement to a meeting. The text is already parsed and cleaned at upload
    time, so no boilerplate is paid for here and nothing is re-parsed.
    """
    return SOURCE_SEPARATOR.join(
        "{0}\n{1}".format(
            DOCUMENT_HEADING_TEMPLATE.format(source["original_name"]),
            source["cleaned_text"],
        )
        for source in source_rows
    )


def generate_report_content(
    conn: sqlite3.Connection, report_id: str
) -> List[Dict[str, Any]]:
    """Draft content for every field the user has not edited, in one call.

    Returns the report's fields in display order after the write. Raises
    ReportNotFoundError for an unknown report, NoSourceDocumentsError when
    nothing has been uploaded yet, and lets app.llm's LLMError subclasses
    propagate untouched so the route layer can answer 502.
    """
    repository.get_report(conn, report_id)
    source_rows = sources.list_sources(conn, report_id)
    if not source_rows:
        raise NoSourceDocumentsError(NO_SOURCES_MESSAGE)
    draftable = [
        field
        for field in fields_repo.list_fields(conn, report_id)
        if not field["is_user_edited"]
    ]
    if not draftable:
        return fields_repo.list_fields(conn, report_id)
    drafted = generate_report_fields(
        build_source_text(source_rows), [field["label"] for field in draftable]
    )
    fields_repo.set_generated_content(
        conn,
        report_id,
        dict(
            (field["id"], drafted.get(field["label"], ""))
            for field in draftable
        ),
    )
    repository.touch_report(conn, report_id)
    return fields_repo.list_fields(conn, report_id)
