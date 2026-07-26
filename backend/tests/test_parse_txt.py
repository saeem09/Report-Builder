import pytest

from app.parsers.errors import DocumentParseError
from app.parsers.plain_text import parse_txt


def test_parse_txt_decodes_utf8_content():
    result = parse_txt("Kickoff meeting\nOwner: Anna".encode("utf-8"))

    assert result == "Kickoff meeting\nOwner: Anna"


def test_parse_txt_strips_the_utf8_byte_order_mark():
    result = parse_txt(b"\xef\xbb\xbfAgenda")

    assert result == "Agenda"


def test_parse_txt_returns_an_empty_string_for_empty_content():
    result = parse_txt(b"")

    assert result == ""


def test_parse_txt_raises_document_parse_error_on_invalid_utf8():
    with pytest.raises(DocumentParseError):
        parse_txt(b"\xff\xfe\x00invalid")
