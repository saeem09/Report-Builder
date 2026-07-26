from pathlib import Path

from .errors import UnsupportedFileTypeError
from .html_document import parse_html
from .pdf_document import parse_pdf
from .plain_text import parse_txt
from .word import parse_docx

PARSERS_BY_EXTENSION = {
    ".txt": parse_txt,
    ".html": parse_html,
    ".docx": parse_docx,
    ".pdf": parse_pdf,
}

SUPPORTED_EXTENSIONS = tuple(sorted(PARSERS_BY_EXTENSION))


def parse_document(content: bytes, filename: str) -> str:
    """Extract plain text from an uploaded file, chosen by its extension.

    filename is only used to pick a parser. Path components are irrelevant
    here because Path().suffix reads the final extension of the last segment,
    so a traversal-style name cannot influence the choice.

    Raises UnsupportedFileTypeError (a DocumentParseError) when the extension
    has no registered parser.
    """
    extension = Path(filename).suffix.lower()
    parser = PARSERS_BY_EXTENSION.get(extension)
    if parser is None:
        raise UnsupportedFileTypeError(
            "Unsupported file type: {0!r}. Supported extensions: {1}.".format(
                filename, ", ".join(SUPPORTED_EXTENSIONS)
            )
        )
    return parser(content)
