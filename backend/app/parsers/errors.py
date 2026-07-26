class DocumentParseError(Exception):
    """Raised when a document cannot be parsed into plain text."""


class UnsupportedFileTypeError(DocumentParseError):
    """Raised when no parser is registered for a file extension."""
