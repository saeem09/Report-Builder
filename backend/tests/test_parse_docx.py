import pytest
from document_builders import build_docx_bytes

from app.parsers.errors import DocumentParseError
from app.parsers.word import parse_docx


def test_parse_docx_returns_paragraph_text_in_order():
    content = build_docx_bytes(["Sprint review", "Attendees: Anna, Ben"])

    result = parse_docx(content)

    assert result == "Sprint review\nAttendees: Anna, Ben"


def test_parse_docx_appends_table_rows_as_tab_separated_lines():
    content = build_docx_bytes(
        ["Action items"], table_rows=(("Task", "Owner"), ("Draft spec", "Anna"))
    )

    result = parse_docx(content)

    assert result == "Action items\nTask\tOwner\nDraft spec\tAnna"


def test_parse_docx_raises_document_parse_error_on_non_docx_bytes():
    with pytest.raises(DocumentParseError):
        parse_docx(b"this is not a docx file")
