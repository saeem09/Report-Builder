from .errors import DocumentParseError

TEXT_ENCODING = "utf-8-sig"


def parse_txt(content: bytes) -> str:
    """Decode a plain text file. Strips a UTF-8 byte order mark if present."""
    try:
        return content.decode(TEXT_ENCODING)
    except UnicodeDecodeError as error:
        raise DocumentParseError(
            "Could not decode the .txt file as UTF-8 text."
        ) from error
