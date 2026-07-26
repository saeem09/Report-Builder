import io

import pdfplumber
from pdfplumber.utils.exceptions import PdfminerException

from .errors import DocumentParseError

PAGE_SEPARATOR = "\n"


def parse_pdf(content: bytes) -> str:
    """Extract text from a PDF, page by page.

    page.extract_text() returns None for a page with no extractable text
    (for example a scanned image), which becomes an empty string here rather
    than a crash. No OCR is attempted in this phase.
    """
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            page_texts = [page.extract_text() or "" for page in pdf.pages]
    except PdfminerException as error:
        raise DocumentParseError("Could not open the file as a PDF document.") from error

    return PAGE_SEPARATOR.join(page_texts)
