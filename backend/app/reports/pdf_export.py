"""Deterministic HTML assembly and PDF rendering. No LLM call happens here.

The layout is a logo, a title, and one heading plus paragraphs per field, so
it is built with str.format and html.escape rather than a template engine. A
template engine would be a new dependency and a new failure mode for about
thirty lines of markup.

build_report_html is a pure function with no native dependency, so HTML
correctness is fully tested without WeasyPrint being involved at all.
"""

import base64
import html
import os
import platform
import re
from typing import Any, Dict, List, Optional

from .errors import PdfExportError

HOMEBREW_LIBRARY_PATH = "/opt/homebrew/lib"
DYLD_FALLBACK_VARIABLE = "DYLD_FALLBACK_LIBRARY_PATH"
DARWIN = "Darwin"

EMPTY_FIELD_PLACEHOLDER = "No content recorded for this field."
DEFAULT_PDF_FILENAME = "report.pdf"
MAX_FILENAME_STEM_LENGTH = 80
PARAGRAPH_SPLIT_PATTERN = re.compile(r"\n\s*\n")
UNSAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")

TEXT_COLOR = "#1C2835"
TITLE_COLOR = "#00496A"
LABEL_COLOR = "#013554"
RULE_COLOR = "#D9D9D9"
MUTED_COLOR = "#7F7F7F"

PAGE_STYLE = """
@page {{ size: A4; margin: 20mm 18mm; }}
body {{
  font-family: Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: {text};
}}
.logo {{ max-height: 64px; max-width: 220px; margin-bottom: 16px; }}
h1 {{ font-size: 22pt; color: {title}; margin: 0 0 4px 0; }}
.rule {{ border-bottom: 1px solid {rule}; margin: 12px 0 20px 0; }}
h2 {{ font-size: 13pt; color: {label}; margin: 0 0 6px 0; }}
section {{ margin-bottom: 20px; page-break-inside: avoid; }}
p {{ margin: 0 0 8px 0; }}
p.empty {{ color: {muted}; font-style: italic; }}
""".format(
    text=TEXT_COLOR,
    title=TITLE_COLOR,
    rule=RULE_COLOR,
    label=LABEL_COLOR,
    muted=MUTED_COLOR,
)

DOCUMENT_TEMPLATE = (
    '<html><head><meta charset="utf-8"><title>{title}</title>'
    "<style>{style}</style></head><body>{logo}"
    '<h1>{title}</h1><div class="rule"></div>{sections}</body></html>'
)


def _ensure_native_library_path() -> None:
    """Make Homebrew's Pango and GObject visible to WeasyPrint on macOS.

    WeasyPrint loads its native libraries through cffi's dlopen, which resolves
    plain names via ctypes.util.find_library. On macOS that helper reads
    DYLD_FALLBACK_LIBRARY_PATH at call time, and Homebrew on Apple Silicon
    installs into /opt/homebrew/lib, which is not on the default search path.
    Setting the variable here, before the import, is the documented fix and was
    verified to work at runtime. Other platforms are left untouched, and no
    library is installed by this function.
    """
    if platform.system() != DARWIN:
        return
    if not os.path.isdir(HOMEBREW_LIBRARY_PATH):
        return
    existing = [
        part
        for part in os.environ.get(DYLD_FALLBACK_VARIABLE, "").split(os.pathsep)
        if part
    ]
    if HOMEBREW_LIBRARY_PATH in existing:
        return
    os.environ[DYLD_FALLBACK_VARIABLE] = os.pathsep.join(
        existing + [HOMEBREW_LIBRARY_PATH]
    )


def _load_weasyprint_html():
    """Import weasyprint.HTML lazily and surface a usable error if it fails.

    The import is deliberately not at module scope: it is slow, and it raises
    OSError rather than ImportError when the native libraries are absent, which
    at module scope would break collection of the entire test suite instead of
    failing one endpoint.
    """
    _ensure_native_library_path()
    from weasyprint import HTML

    return HTML


def build_logo_data_uri(logo_bytes: bytes, content_type: str) -> str:
    """Inline an image so the rendered HTML fetches nothing over the network."""
    encoded = base64.b64encode(logo_bytes).decode("ascii")
    return "data:{0};base64,{1}".format(content_type, encoded)


def _render_paragraphs(content: str) -> str:
    """Turn plain text into escaped paragraphs, one per blank-line-separated block.

    Field content is plain prose: the LLM system prompt forbids markdown and
    the user edits it as plain text. Everything is escaped, so no user or model
    output can inject markup into the PDF.
    """
    blocks = [
        block.strip()
        for block in PARAGRAPH_SPLIT_PATTERN.split(content)
        if block.strip()
    ]
    if not blocks:
        return '<p class="empty">{0}</p>'.format(
            html.escape(EMPTY_FIELD_PLACEHOLDER)
        )
    return "".join(
        "<p>{0}</p>".format(html.escape(block).replace("\n", "<br>"))
        for block in blocks
    )


def build_report_html(
    report_name: str,
    report_fields: List[Dict[str, Any]],
    logo_data_uri: Optional[str] = None,
) -> str:
    """Build the printable HTML for one report, in the order fields are given."""
    logo_markup = ""
    if logo_data_uri:
        logo_markup = '<img class="logo" src="{0}" alt="Company logo">'.format(
            logo_data_uri
        )
    sections = "".join(
        "<section><h2>{0}</h2>{1}</section>".format(
            html.escape(field["label"]), _render_paragraphs(field["content"])
        )
        for field in report_fields
    )
    return DOCUMENT_TEMPLATE.format(
        title=html.escape(report_name),
        style=PAGE_STYLE,
        logo=logo_markup,
        sections=sections,
    )


def build_pdf_filename(report_name: str) -> str:
    """Slugify a report name into a download filename.

    The result lands in a Content-Disposition response header, and report names
    are freeform user input. Starlette does not escape header values, so a name
    containing a quote, a semicolon, or CRLF would be a header-injection
    vector. A strict allowlist of [A-Za-z0-9._-] is unambiguously safe.
    """
    slug = UNSAFE_FILENAME_PATTERN.sub("-", report_name).strip("-.")
    stem = slug[:MAX_FILENAME_STEM_LENGTH].strip("-.")
    if not stem:
        return DEFAULT_PDF_FILENAME
    return "{0}.pdf".format(stem)


def render_report_pdf(
    report_name: str,
    report_fields: List[Dict[str, Any]],
    logo_bytes: Optional[bytes] = None,
    logo_content_type: Optional[str] = None,
) -> bytes:
    """Render one report to PDF bytes.

    Raises PdfExportError when WeasyPrint cannot be loaded or the render
    fails, so the route layer can answer with a clear message instead of an
    opaque native-library traceback.
    """
    logo_data_uri = None
    if logo_bytes and logo_content_type:
        logo_data_uri = build_logo_data_uri(logo_bytes, logo_content_type)
    document_html = build_report_html(report_name, report_fields, logo_data_uri)
    try:
        html_class = _load_weasyprint_html()
        return html_class(string=document_html).write_pdf()
    except Exception as error:
        raise PdfExportError(
            "The report could not be rendered to PDF: {0}".format(
                type(error).__name__
            )
        ) from error
