import io
import zipfile

import pytest
from document_builders import build_docx_bytes

from app.parsers.dispatcher import parse_document
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


def test_parse_docx_returns_empty_string_for_an_empty_document():
    content = build_docx_bytes([])

    result = parse_docx(content)

    assert result == ""


def test_parse_docx_returns_only_table_content_when_there_are_no_paragraphs():
    content = build_docx_bytes([], table_rows=(("a", "b"),))

    result = parse_docx(content)

    assert result == "a\tb"


def _build_well_formed_zip_missing_ooxml_parts() -> bytes:
    """A structurally valid ZIP archive that is not an OOXML package.

    python-docx (via python-opc) assumes any ZIP handed to it has an OOXML
    part structure and indexes straight into the archive for
    '[Content_Types].xml'. A well-formed ZIP that simply lacks that member
    makes that lookup raise a bare KeyError instead of one of the exceptions
    (BadZipFile, PackageNotFoundError, ValueError) parse_docx already
    anticipates.

    parse_docx itself is intentionally NOT widened to catch this: the fix is
    structural, at the dispatcher level (parse_document), so that every
    parser gets the same safety net instead of patching this one library
    surprise. Calling parse_docx directly therefore still lets the bare
    KeyError through - only parse_document converts it.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("arbitrary.txt", "hello world")
    return buffer.getvalue()


def test_parse_document_converts_well_formed_non_ooxml_zip_to_document_parse_error():
    content = _build_well_formed_zip_missing_ooxml_parts()

    with pytest.raises(DocumentParseError) as error_info:
        parse_document(content, "notes.docx")

    message = str(error_info.value)
    assert "notes.docx" in message
    assert "KeyError" in message
