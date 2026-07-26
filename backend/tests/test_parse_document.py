import pytest
from document_builders import SINGLE_PAGE_PDF_BYTES, build_docx_bytes

from app.parsers import (
    SUPPORTED_EXTENSIONS,
    DocumentParseError,
    UnsupportedFileTypeError,
    parse_document,
)


def test_parse_document_dispatches_txt_files():
    assert parse_document(b"Kickoff notes", "notes.txt") == "Kickoff notes"


def test_parse_document_dispatches_html_files():
    assert parse_document(b"<p>Kickoff notes</p>", "notes.html") == "Kickoff notes"


def test_parse_document_dispatches_docx_files():
    content = build_docx_bytes(["Kickoff notes"])

    assert parse_document(content, "notes.docx") == "Kickoff notes"


def test_parse_document_dispatches_pdf_files():
    assert parse_document(SINGLE_PAGE_PDF_BYTES, "notes.pdf") == "Sprint review notes"


def test_parse_document_matches_extensions_case_insensitively():
    assert parse_document(b"Kickoff notes", "NOTES.TXT") == "Kickoff notes"


def test_parse_document_uses_only_the_final_extension():
    assert parse_document(b"Kickoff notes", "archive.pdf.txt") == "Kickoff notes"


def test_parse_document_raises_unsupported_file_type_error_for_unknown_extension():
    with pytest.raises(UnsupportedFileTypeError) as error_info:
        parse_document(b"anything", "notes.doc")

    message = str(error_info.value)
    assert "notes.doc" in message
    for extension in SUPPORTED_EXTENSIONS:
        assert extension in message


def test_parse_document_raises_unsupported_file_type_error_for_missing_extension():
    with pytest.raises(UnsupportedFileTypeError):
        parse_document(b"anything", "notes")


def test_unsupported_file_type_error_is_a_document_parse_error():
    assert issubclass(UnsupportedFileTypeError, DocumentParseError)


def test_supported_extensions_lists_the_four_input_formats():
    assert SUPPORTED_EXTENSIONS == (".docx", ".html", ".pdf", ".txt")
