"""Prompt text for report field generation.

REPORT_FIELD_SYSTEM_PROMPT is sent as a cached system block, so it must stay
byte-identical across requests. Anything that varies per request belongs in
the user prompt built by build_report_field_prompt.
"""

from typing import List

REPORT_FIELD_SYSTEM_PROMPT = (
    "You are a business analyst who drafts progress report content from "
    "meeting notes, transcripts, and shared project documents.\n"
    "Follow these rules for every request:\n"
    "- Write only from the supplied source text. Never invent facts, names, "
    "dates, or numbers that the source does not contain.\n"
    "- If the source text says nothing about a field, return an empty string "
    "for that field rather than guessing.\n"
    "- Write plain prose. Do not use markdown headings, bullet characters, or "
    "emojis.\n"
    "- Keep each field focused on its own label. Do not repeat the same "
    "sentences across several fields.\n"
    "- Record content for every requested label in a single tool call."
)

SOURCE_TEXT_HEADING = "Source material:"
FIELD_LABELS_HEADING = "Report fields to draft, one entry per label:"


def build_report_field_prompt(source_text: str, field_labels: List[str]) -> str:
    """Build the per-request user prompt.

    The source text comes first so the labels read as instructions applied to
    material the model has already seen.
    """
    label_lines = "\n".join("- {0}".format(label) for label in field_labels)
    return "{0}\n{1}\n\n{2}\n{3}".format(
        SOURCE_TEXT_HEADING, source_text, FIELD_LABELS_HEADING, label_lines
    )
