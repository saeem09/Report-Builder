"""Whitespace normalization for parsed document text.

This is preprocessing groundwork for the later LLM step: fewer redundant
whitespace tokens means a cheaper prompt. It performs pure string work and
must never call an LLM or any network API.
"""

import re

MAX_CONSECUTIVE_BLANK_LINES = 1

_LINE_BREAK_PATTERN = re.compile(r"\r\n?")
_REPEATED_SPACE_PATTERN = re.compile(r" {2,}")
_EXCESS_BLANK_LINE_PATTERN = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    """Return a whitespace-normalized copy of text.

    Line endings are normalized to "\\n", runs of spaces collapse to one,
    each line is stripped, runs of blank lines collapse to at most
    MAX_CONSECUTIVE_BLANK_LINES, and leading and trailing blank lines are
    removed. Tabs inside a line are preserved because the Word parser uses
    them as the cell separator for table rows. The input string is never
    mutated; a new string is returned.
    """
    normalized = _LINE_BREAK_PATTERN.sub("\n", text)
    stripped_lines = tuple(
        _REPEATED_SPACE_PATTERN.sub(" ", line).strip()
        for line in normalized.split("\n")
    )
    collapsed = _EXCESS_BLANK_LINE_PATTERN.sub(
        "\n" * (MAX_CONSECUTIVE_BLANK_LINES + 1), "\n".join(stripped_lines)
    )
    return collapsed.strip()
