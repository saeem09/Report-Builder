import base64

import pytest

from app.reports import pdf_export
from app.reports.errors import PdfExportError

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGA"
    "hKmMIQAAAABJRU5ErkJggg=="
)


def field(label, content, sort_order=0):
    return {
        "id": "f{0}".format(sort_order),
        "report_id": "r1",
        "label": label,
        "content": content,
        "sort_order": sort_order,
        "is_user_edited": 0,
    }


def test_build_logo_data_uri_embeds_base64_png():
    uri = pdf_export.build_logo_data_uri(PNG_BYTES, "image/png")

    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == PNG_BYTES


def test_html_contains_the_report_name_and_every_label():
    html = pdf_export.build_report_html(
        "Kickoff", [field("Summary", "Held."), field("Blockers", "None.", 1)]
    )

    assert "Kickoff" in html
    assert "Summary" in html
    assert "Blockers" in html
    assert "Held." in html


def test_html_keeps_fields_in_the_given_order():
    html = pdf_export.build_report_html(
        "Kickoff", [field("Summary", "a"), field("Blockers", "b", 1)]
    )

    assert html.index("Summary") < html.index("Blockers")


def test_html_escapes_the_report_name():
    html = pdf_export.build_report_html("<script>alert(1)</script>", [])

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_html_escapes_field_labels_and_content():
    html = pdf_export.build_report_html(
        "Kickoff", [field("A & B", "5 < 6 and \"quoted\"")]
    )

    assert "A &amp; B" in html
    assert "5 &lt; 6" in html


def test_html_renders_each_paragraph_separately():
    html = pdf_export.build_report_html(
        "Kickoff", [field("Summary", "First para.\n\nSecond para.")]
    )

    assert "<p>First para.</p>" in html
    assert "<p>Second para.</p>" in html


def test_html_shows_a_placeholder_for_empty_content():
    html = pdf_export.build_report_html("Kickoff", [field("Summary", "")])

    assert pdf_export.EMPTY_FIELD_PLACEHOLDER in html


def test_html_shows_a_placeholder_for_whitespace_only_content():
    html = pdf_export.build_report_html("Kickoff", [field("Summary", "   \n  ")])

    assert pdf_export.EMPTY_FIELD_PLACEHOLDER in html


def test_html_omits_the_logo_element_when_there_is_no_logo():
    html = pdf_export.build_report_html("Kickoff", [])

    assert "<img" not in html


def test_html_includes_the_logo_when_given():
    uri = pdf_export.build_logo_data_uri(PNG_BYTES, "image/png")

    html = pdf_export.build_report_html("Kickoff", [], logo_data_uri=uri)

    assert "<img" in html
    assert uri in html


def test_html_handles_a_report_with_no_fields():
    html = pdf_export.build_report_html("Kickoff", [])

    assert "Kickoff" in html
    assert "<html" in html


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Q3 Kickoff Review", "Q3-Kickoff-Review.pdf"),
        ('a"; X-Evil: 1', "a-X-Evil-1.pdf"),
        ("../../etc/passwd", "etc-passwd.pdf"),
        ("   ", "report.pdf"),
        ("...", "report.pdf"),
    ],
)
def test_build_pdf_filename_slugifies_unsafe_names(name, expected):
    assert pdf_export.build_pdf_filename(name) == expected


def test_build_pdf_filename_never_contains_a_header_breaking_character():
    result = pdf_export.build_pdf_filename('bad\r\nX-Evil: 1"name')

    for character in ('"', "\r", "\n", ";", " "):
        assert character not in result


def test_build_pdf_filename_is_length_bounded():
    assert len(pdf_export.build_pdf_filename("x" * 500)) <= 84


def test_render_report_pdf_produces_valid_pdf_bytes():
    pdf = pdf_export.render_report_pdf(
        "Kickoff", [field("Summary", "Held."), field("Blockers", "None.", 1)]
    )

    assert isinstance(pdf, bytes)
    assert pdf.startswith(b"%PDF-")
    assert b"%%EOF" in pdf[-2048:]
    assert len(pdf) > 1000


def test_render_report_pdf_embeds_the_logo():
    without_logo = pdf_export.render_report_pdf("Kickoff", [field("Summary", "a")])
    with_logo = pdf_export.render_report_pdf(
        "Kickoff",
        [field("Summary", "a")],
        logo_bytes=PNG_BYTES,
        logo_content_type="image/png",
    )

    assert len(with_logo) > len(without_logo)


def test_render_report_pdf_handles_a_report_with_no_fields():
    pdf = pdf_export.render_report_pdf("Kickoff", [])

    assert pdf.startswith(b"%PDF-")


def test_render_report_pdf_raises_pdf_export_error_when_weasyprint_is_missing(
    monkeypatch,
):
    def explode():
        raise ImportError("no weasyprint here")

    monkeypatch.setattr(pdf_export, "_load_weasyprint_html", explode)

    with pytest.raises(PdfExportError):
        pdf_export.render_report_pdf("Kickoff", [])


def test_ensure_native_library_path_is_idempotent(monkeypatch):
    monkeypatch.setenv(pdf_export.DYLD_FALLBACK_VARIABLE, "")

    pdf_export._ensure_native_library_path()
    first = __import__("os").environ.get(pdf_export.DYLD_FALLBACK_VARIABLE, "")
    pdf_export._ensure_native_library_path()
    second = __import__("os").environ.get(pdf_export.DYLD_FALLBACK_VARIABLE, "")

    assert first == second
