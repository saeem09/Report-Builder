"""Domain errors for the progress report API.

Each of these is mapped to exactly one HTTP status code by
app.reports.exception_handlers, so route handlers never build an
HTTPException for a condition the data layer already describes precisely.
"""


class ReportError(Exception):
    """Base class for every failure raised by the app.reports package."""


class ReportNotFoundError(ReportError):
    """Raised when a report id does not exist."""


class FieldNotFoundError(ReportError):
    """Raised when a field id does not exist on the given report."""


class FieldOrderMismatchError(ReportError):
    """Raised when a reorder request does not list every field exactly once."""


class NoSourceDocumentsError(ReportError):
    """Raised when generation is triggered before any document was uploaded."""


class PdfExportError(ReportError):
    """Raised when the report could not be rendered to PDF."""
