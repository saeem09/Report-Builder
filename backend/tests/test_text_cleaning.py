from app.text_cleaning import clean_text


def test_clean_text_normalizes_windows_and_classic_mac_line_endings():
    result = clean_text("first\r\nsecond\rthird")

    assert result == "first\nsecond\nthird"


def test_clean_text_strips_leading_and_trailing_whitespace_per_line():
    result = clean_text("   Agenda   \n\t Owner: Anna \t")

    assert result == "Agenda\nOwner: Anna"


def test_clean_text_collapses_runs_of_spaces_but_keeps_tabs_between_cells():
    result = clean_text("Task     Owner\nDraft\tAnna")

    assert result == "Task Owner\nDraft\tAnna"


def test_clean_text_collapses_repeated_blank_lines_to_one():
    result = clean_text("first\n\n\n\n\nsecond")

    assert result == "first\n\nsecond"


def test_clean_text_trims_leading_and_trailing_blank_lines():
    result = clean_text("\n\n  Agenda  \n\n")

    assert result == "Agenda"


def test_clean_text_returns_empty_string_for_whitespace_only_input():
    result = clean_text("   \n\t\n  ")

    assert result == ""
