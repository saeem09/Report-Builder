"""One place that maps a domain exception to an HTTP status code.

Route handlers therefore never build an HTTPException for a condition the data
layer already describes precisely: they call a repository function and let it
raise. The response body is FastAPI's native {"detail": ...} shape, the same
shape FastAPI already emits for HTTPException and for 422 validation errors,
so the API speaks one error language everywhere.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..llm import LLMError
from ..parsers import DocumentParseError
from .errors import (
    FieldNotFoundError,
    FieldOrderMismatchError,
    NoSourceDocumentsError,
    PdfExportError,
    ReportNotFoundError,
)

LLM_UPSTREAM_MESSAGE = (
    "The AI service could not draft this report. Please try again."
)
PDF_EXPORT_STATUS_CODE = 500
LLM_STATUS_CODE = 502

ERROR_STATUS_CODES = (
    (ReportNotFoundError, 404),
    (FieldNotFoundError, 404),
    (FieldOrderMismatchError, 400),
    (NoSourceDocumentsError, 409),
    (PdfExportError, PDF_EXPORT_STATUS_CODE),
    (DocumentParseError, 400),
)


def _build_handler(status_code: int):
    """Build a handler that renders the exception message as {"detail": ...}."""

    def handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


def _llm_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render an upstream LLM failure without echoing the provider's message.

    app.llm already guarantees its messages carry no API key, but the provider
    class name is still an internal detail, so the client sees a fixed message
    instead.
    """
    return JSONResponse(
        status_code=LLM_STATUS_CODE, content={"detail": LLM_UPSTREAM_MESSAGE}
    )


def register_exception_handlers(application: FastAPI) -> None:
    """Attach every domain-error handler to the application.

    UnsupportedFileTypeError subclasses DocumentParseError, so registering the
    base class covers both.
    """
    for error_class, status_code in ERROR_STATUS_CODES:
        application.add_exception_handler(error_class, _build_handler(status_code))
    application.add_exception_handler(LLMError, _llm_handler)
