"""Batched, structured drafting of progress report field content.

One Claude call covers every field of one report, per the batch-generation
rule in AGENTS.md. Structured output is obtained by forcing a tool call rather
than parsing prose, so the label-to-content mapping is reliable.
"""

from types import MappingProxyType
from typing import Any, Dict, List, Optional

from .client import ClaudeClient
from .prompts import REPORT_FIELD_SYSTEM_PROMPT, build_report_field_prompt

REPORT_FIELD_TOOL_NAME = "record_report_fields"

REPORT_FIELD_TOOL = MappingProxyType({
    "name": REPORT_FIELD_TOOL_NAME,
    "description": (
        "Record the drafted content for every requested progress report field. "
        "Call this exactly once, with one entry per requested label."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "fields": {
                "type": "array",
                "description": (
                    "One entry per requested field label, in the order the "
                    "labels were given."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {
                            "type": "string",
                            "description": (
                                "The requested field label, copied verbatim."
                            ),
                        },
                        "content": {
                            "type": "string",
                            "description": (
                                "The drafted plain text content for this field. "
                                "Use an empty string when the source text does "
                                "not cover the field."
                            ),
                        },
                    },
                    "required": ["label", "content"],
                },
            }
        },
        "required": ["fields"],
    },
})


def _validate_inputs(source_text: Any, field_labels: Any) -> None:
    """Reject shapes generate_report_fields cannot safely process.

    Raises ValueError when source_text is not a string, is blank, when
    field_labels is a bare string (a plausible caller mistake: a string is
    iterable over single characters, so it would otherwise silently pass
    through as a list of one-character labels and trigger a real, billable
    Claude call with garbage labels), when field_labels is not a list/tuple,
    or when any element of field_labels is not a string.
    """
    if not isinstance(source_text, str):
        raise ValueError("source_text must be a string.")
    if not source_text.strip():
        raise ValueError("source_text must contain non-whitespace characters.")
    if isinstance(field_labels, str):
        raise ValueError(
            "field_labels must be a list or tuple of strings, not a bare string."
        )
    if not isinstance(field_labels, (list, tuple)):
        raise ValueError("field_labels must be a list or tuple of strings.")
    if not all(isinstance(label, str) for label in field_labels):
        raise ValueError("Every element of field_labels must be a string.")


def _unique_labels(field_labels: List[str]) -> List[str]:
    """Return the labels with duplicates removed, original order preserved."""
    unique = []
    for label in field_labels:
        if label not in unique:
            unique.append(label)
    return unique


def _content_by_label(
    tool_input: Dict[str, Any], requested: List[str]
) -> Dict[str, str]:
    """Reconcile Claude's entries against the labels that were requested.

    The result always has exactly one key per requested label. Entries for
    labels nobody asked for are dropped, repeated labels keep the first
    entry, and malformed entries are skipped so their label falls back to an
    empty draft the user can fill in.
    """
    entries = tool_input.get("fields")
    drafted = {}
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            content = entry.get("content")
            if not isinstance(label, str) or not isinstance(content, str):
                continue
            if label not in requested or label in drafted:
                continue
            drafted[label] = content
    return dict((label, drafted.get(label, "")) for label in requested)


def generate_report_fields(
    source_text: str,
    field_labels: List[str],
    client: Optional[ClaudeClient] = None,
) -> Dict[str, str]:
    """Draft content for every field label from one block of source text.

    source_text should already be parsed and cleaned (see app.parsers and
    app.text_cleaning) so no tokens are spent on boilerplate. Exactly one
    Claude call is made, covering all labels at once. Passing no labels returns
    an empty dict without calling Claude at all.

    Raises ValueError when source_text is not a string or is blank, when
    field_labels is not a list/tuple (a bare string included, since it is
    otherwise silently iterable into single-character labels) or contains a
    non-string element, LLMConfigurationError when the API key is missing,
    LLMRequestError when the API call fails, and LLMResponseError when Claude
    does not return the forced tool call.
    """
    _validate_inputs(source_text, field_labels)
    requested = _unique_labels([label for label in field_labels if label.strip()])
    if not requested:
        return {}
    active_client = ClaudeClient() if client is None else client
    tool_input = active_client.request_tool_call(
        system_prompt=REPORT_FIELD_SYSTEM_PROMPT,
        user_prompt=build_report_field_prompt(source_text, requested),
        tool=REPORT_FIELD_TOOL,
        tool_name=REPORT_FIELD_TOOL_NAME,
    )
    return _content_by_label(tool_input, requested)
