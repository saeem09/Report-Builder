from app.llm.prompts import (
    FIELD_LABELS_HEADING,
    REPORT_FIELD_SYSTEM_PROMPT,
    SOURCE_TEXT_HEADING,
    build_report_field_prompt,
)


def test_system_prompt_forbids_invented_facts():
    assert "Never invent" in REPORT_FIELD_SYSTEM_PROMPT


def test_system_prompt_asks_for_a_single_batched_tool_call():
    assert "single tool call" in REPORT_FIELD_SYSTEM_PROMPT


def test_system_prompt_is_stable_across_calls():
    assert REPORT_FIELD_SYSTEM_PROMPT is REPORT_FIELD_SYSTEM_PROMPT
    assert "{" not in REPORT_FIELD_SYSTEM_PROMPT


def test_prompt_contains_the_source_text_and_both_headings():
    result = build_report_field_prompt("Kickoff notes.", ["Summary"])

    assert SOURCE_TEXT_HEADING in result
    assert FIELD_LABELS_HEADING in result
    assert "Kickoff notes." in result


def test_prompt_lists_every_label_on_its_own_line():
    result = build_report_field_prompt("Notes.", ["Summary", "Blockers"])

    assert "- Summary" in result
    assert "- Blockers" in result


def test_prompt_preserves_label_order():
    result = build_report_field_prompt("Notes.", ["Blockers", "Summary"])

    assert result.index("- Blockers") < result.index("- Summary")


def test_prompt_puts_the_source_text_before_the_labels():
    result = build_report_field_prompt("Notes.", ["Summary"])

    assert result.index(SOURCE_TEXT_HEADING) < result.index(FIELD_LABELS_HEADING)


def test_prompt_handles_a_single_label():
    result = build_report_field_prompt("Notes.", ["Summary"])

    assert result.count("- ") == 1
