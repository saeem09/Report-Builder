import pytest
from document_builders import NO_TEXT_PDF_BYTES, SINGLE_PAGE_PDF_BYTES, TWO_PAGE_PDF_BYTES

from app.parsers.errors import DocumentParseError
from app.parsers.pdf_document import parse_pdf


def test_parse_pdf_extracts_text_from_a_single_page():
    result = parse_pdf(SINGLE_PAGE_PDF_BYTES)

    assert result == "Sprint review notes"


def test_parse_pdf_joins_pages_with_a_newline():
    result = parse_pdf(TWO_PAGE_PDF_BYTES)

    assert result == "Sprint review notes\nAction items"


def test_parse_pdf_raises_document_parse_error_on_non_pdf_bytes():
    with pytest.raises(DocumentParseError):
        parse_pdf(b"this is not a pdf file")


def test_parse_pdf_returns_empty_string_for_a_page_with_no_extractable_text():
    result = parse_pdf(NO_TEXT_PDF_BYTES)

    assert result == ""
