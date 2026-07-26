"""Batched, structured drafting of progress report field content.

One Claude call covers every field of one report, per the batch-generation
rule in AGENTS.md. Structured output is obtained by forcing a tool call rather
than parsing prose, so the label-to-content mapping is reliable.
"""

from typing import Any, Dict, List, Optional

from .client import ClaudeClient
from .prompts import REPORT_FIELD_SYSTEM_PROMPT, build_report_field_prompt

REPORT_FIELD_TOOL_NAME = "record_report_fields"

REPORT_FIELD_TOOL = {
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
}


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

    Raises ValueError when source_text is blank, LLMConfigurationError when the
    API key is missing, LLMRequestError when the API call fails, and
    LLMResponseError when Claude does not return the forced tool call.
    """
    if not source_text.strip():
        raise ValueError("source_text must contain non-whitespace characters.")
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
