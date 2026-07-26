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


def test_parse_document_passes_through_a_parsers_own_document_parse_error():
    # Invalid UTF-8 bytes make parse_txt raise its own specific
    # DocumentParseError. The dispatcher's catch-all must not swallow or
    # rewrap an error a parser already converted deliberately - it should
    # pass through unchanged.
    with pytest.raises(DocumentParseError) as error_info:
        parse_document(b"\xff\xfe\x00\x81", "notes.txt")

    assert "Could not decode the .txt file as UTF-8 text." in str(error_info.value)


def test_supported_extensions_lists_the_four_input_formats():
    assert SUPPORTED_EXTENSIONS == (".docx", ".html", ".pdf", ".txt")


def test_parsers_by_extension_is_immutable():
    from app.parsers import PARSERS_BY_EXTENSION

    with pytest.raises(TypeError):
        PARSERS_BY_EXTENSION[".evil"] = None
