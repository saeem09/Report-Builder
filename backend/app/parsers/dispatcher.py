from pathlib import Path
from types import MappingProxyType

from .errors import DocumentParseError, UnsupportedFileTypeError
from .html_document import parse_html
from .pdf_document import parse_pdf
from .plain_text import parse_txt
from .word import parse_docx

PARSERS_BY_EXTENSION = MappingProxyType(
    {
        ".txt": parse_txt,
        ".html": parse_html,
        ".docx": parse_docx,
        ".pdf": parse_pdf,
    }
)

SUPPORTED_EXTENSIONS = tuple(sorted(PARSERS_BY_EXTENSION))


def parse_document(content: bytes, filename: str) -> str:
    """Extract plain text from an uploaded file, chosen by its extension.

    filename is only used to pick a parser. Path components are irrelevant
    here because Path().suffix reads the final extension of the last segment,
    so a traversal-style name cannot influence the choice.

    Raises UnsupportedFileTypeError (a DocumentParseError) when the extension
    has no registered parser.

    Every other failure is also guaranteed to surface as a DocumentParseError:
    each parser already converts the library exceptions it knows about into a
    specific, helpful DocumentParseError, but a parsing library can always
    raise something unanticipated (e.g. a well-formed ZIP that is not a valid
    OOXML package makes python-docx raise a bare KeyError instead of one of
    the exceptions word.py catches). This catch-all is the safety net
    underneath those per-parser conversions, not a replacement for them.
    """
    extension = Path(filename).suffix.lower()
    parser = PARSERS_BY_EXTENSION.get(extension)
    if parser is None:
        raise UnsupportedFileTypeError(
            "Unsupported file type: {0!r}. Supported extensions: {1}.".format(
                filename, ", ".join(SUPPORTED_EXTENSIONS)
            )
        )
    try:
        return parser(content)
    except DocumentParseError:
        raise
    except Exception as error:
        raise DocumentParseError(
            "Could not parse {0!r}: unexpected {1}: {2}".format(
                filename, type(error).__name__, error
            )
        ) from error
