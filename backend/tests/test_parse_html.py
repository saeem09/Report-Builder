from app.parsers.html_document import parse_html


def test_parse_html_extracts_visible_text():
    content = b"<html><body><h1>Sprint review</h1><p>Backlog groomed.</p></body></html>"

    result = parse_html(content)

    assert "Sprint review" in result
    assert "Backlog groomed." in result


def test_parse_html_drops_script_and_style_content():
    content = (
        b"<html><head><style>h1 { color: #000; }</style></head>"
        b"<body><script>console.log('x')</script><h1>Agenda</h1></body></html>"
    )

    result = parse_html(content)

    assert "Agenda" in result
    assert "console.log" not in result
    assert "color" not in result


def test_parse_html_does_not_return_markup():
    result = parse_html(b"<p>Decision <strong>approved</strong></p>")

    assert "<" not in result
    assert "Decision" in result
    assert "approved" in result


def test_parse_html_separates_block_text_with_newlines():
    result = parse_html(b"<p>First</p><p>Second</p>")

    assert result == "First\nSecond"
