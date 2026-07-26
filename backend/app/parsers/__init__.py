"""Deterministic document parsing. No LLM calls happen anywhere in this package."""

from .dispatcher import PARSERS_BY_EXTENSION, SUPPORTED_EXTENSIONS, parse_document
from .errors import DocumentParseError, UnsupportedFileTypeError
from .html_document import parse_html
from .pdf_document import parse_pdf
from .plain_text import parse_txt
from .word import parse_docx

__all__ = [
    "PARSERS_BY_EXTENSION",
    "SUPPORTED_EXTENSIONS",
    "DocumentParseError",
    "UnsupportedFileTypeError",
    "parse_document",
    "parse_docx",
    "parse_html",
    "parse_pdf",
    "parse_txt",
]
