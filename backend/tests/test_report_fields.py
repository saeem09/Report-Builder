import pytest
from llm_doubles import FakeAnthropicClient, build_tool_use_message

from app.llm.client import ClaudeClient
from app.llm.prompts import REPORT_FIELD_SYSTEM_PROMPT
from app.llm.report_fields import (
    REPORT_FIELD_TOOL,
    REPORT_FIELD_TOOL_NAME,
    generate_report_fields,
)

SOURCE = "Kickoff meeting. Anna owns the spec. Ben reported the API is blocked."


def make_client(fields):
    """Build a ClaudeClient whose next response records the given field entries."""
    api_client = FakeAnthropicClient(
        response=build_tool_use_message(REPORT_FIELD_TOOL_NAME, {"fields": fields})
    )
    return ClaudeClient(api_client=api_client), api_client


def test_returns_content_for_every_requested_label():
    client, _ = make_client(
        [
            {"label": "Summary", "content": "Kickoff held."},
            {"label": "Blockers", "content": "API access is blocked."},
        ]
    )

    result = generate_report_fields(SOURCE, ["Summary", "Blockers"], client=client)

    assert result == {
        "Summary": "Kickoff held.",
        "Blockers": "API access is blocked.",
    }


def test_generates_all_fields_in_one_claude_call():
    client, api_client = make_client(
        [
            {"label": "Summary", "content": "a"},
            {"label": "Blockers", "content": "b"},
            {"label": "Next steps", "content": "c"},
        ]
    )

    generate_report_fields(
        SOURCE, ["Summary", "Blockers", "Next steps"], client=client
    )

    assert len(api_client.messages.calls) == 1


def test_request_uses_the_forced_report_field_tool_and_cached_system_prompt():
    client, api_client = make_client([{"label": "Summary", "content": "a"}])

    generate_report_fields(SOURCE, ["Summary"], client=client)

    request = api_client.messages.calls[0]
    assert request["tools"] == [REPORT_FIELD_TOOL]
    assert request["tool_choice"] == {"type": "tool", "name": REPORT_FIELD_TOOL_NAME}
    assert request["system"][0]["text"] == REPORT_FIELD_SYSTEM_PROMPT
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_user_prompt_carries_the_source_text_and_every_label():
    client, api_client = make_client([{"label": "Summary", "content": "a"}])

    generate_report_fields(SOURCE, ["Summary", "Blockers"], client=client)

    prompt = api_client.messages.calls[0]["messages"][0]["content"]
    assert SOURCE in prompt
    assert "- Summary" in prompt
    assert "- Blockers" in prompt


def test_missing_field_in_the_response_becomes_an_empty_string():
    client, _ = make_client([{"label": "Summary", "content": "Kickoff held."}])

    result = generate_report_fields(SOURCE, ["Summary", "Blockers"], client=client)

    assert result == {"Summary": "Kickoff held.", "Blockers": ""}


def test_unrequested_field_in_the_response_is_dropped():
    client, _ = make_client(
        [
            {"label": "Summary", "content": "Kickoff held."},
            {"label": "Budget", "content": "Not requested."},
        ]
    )

    result = generate_report_fields(SOURCE, ["Summary"], client=client)

    assert result == {"Summary": "Kickoff held."}


def test_duplicate_labels_in_the_response_keep_the_first_entry():
    client, _ = make_client(
        [
            {"label": "Summary", "content": "first"},
            {"label": "Summary", "content": "second"},
        ]
    )

    result = generate_report_fields(SOURCE, ["Summary"], client=client)

    assert result == {"Summary": "first"}


def test_duplicate_requested_labels_are_requested_once():
    client, api_client = make_client([{"label": "Summary", "content": "a"}])

    result = generate_report_fields(SOURCE, ["Summary", "Summary"], client=client)

    assert result == {"Summary": "a"}
    prompt = api_client.messages.calls[0]["messages"][0]["content"]
    assert prompt.count("- Summary") == 1


@pytest.mark.parametrize(
    "entries",
    [
        [{"label": "Summary"}],
        [{"content": "orphan"}],
        [{"label": "Summary", "content": 42}],
        ["not an object"],
        [],
    ],
)
def test_malformed_entries_fall_back_to_empty_content(entries):
    client, _ = make_client(entries)

    result = generate_report_fields(SOURCE, ["Summary"], client=client)

    assert result == {"Summary": ""}


def test_missing_fields_key_falls_back_to_empty_content():
    api_client = FakeAnthropicClient(
        response=build_tool_use_message(REPORT_FIELD_TOOL_NAME, {"other": []})
    )
    client = ClaudeClient(api_client=api_client)

    result = generate_report_fields(SOURCE, ["Summary"], client=client)

    assert result == {"Summary": ""}


def test_empty_label_list_returns_empty_dict_without_calling_claude():
    client, api_client = make_client([])

    assert generate_report_fields(SOURCE, [], client=client) == {}
    assert api_client.messages.calls == []


def test_blank_labels_are_ignored():
    client, api_client = make_client([])

    assert generate_report_fields(SOURCE, ["  ", ""], client=client) == {}
    assert api_client.messages.calls == []


def test_blank_source_text_raises_value_error():
    client, _ = make_client([])

    with pytest.raises(ValueError):
        generate_report_fields("   \n ", ["Summary"], client=client)


@pytest.mark.parametrize("bad_source_text", [None, 123, ["notes"], {"a": 1}])
def test_non_string_source_text_raises_value_error(bad_source_text):
    client, api_client = make_client([])

    with pytest.raises(ValueError):
        generate_report_fields(bad_source_text, ["Summary"], client=client)

    assert api_client.messages.calls == []


def test_bare_string_field_labels_raises_value_error_instead_of_calling_claude():
    client, api_client = make_client([])

    with pytest.raises(ValueError):
        generate_report_fields(SOURCE, "Summary", client=client)

    assert api_client.messages.calls == []


@pytest.mark.parametrize("bad_field_labels", [123, {"Summary": 1}, None, 4.5])
def test_non_list_field_labels_raises_value_error(bad_field_labels):
    client, api_client = make_client([])

    with pytest.raises(ValueError):
        generate_report_fields(SOURCE, bad_field_labels, client=client)

    assert api_client.messages.calls == []


@pytest.mark.parametrize("bad_labels", [[123], ["Summary", None], [1.5, "Blockers"]])
def test_field_labels_with_a_non_string_element_raises_value_error(bad_labels):
    client, api_client = make_client([])

    with pytest.raises(ValueError):
        generate_report_fields(SOURCE, bad_labels, client=client)

    assert api_client.messages.calls == []


def test_report_field_tool_is_immutable():
    with pytest.raises(TypeError):
        REPORT_FIELD_TOOL["name"] = "poisoned"


def test_tool_schema_requires_label_and_content_strings():
    items = REPORT_FIELD_TOOL["input_schema"]["properties"]["fields"]["items"]

    assert items["required"] == ["label", "content"]
    assert items["properties"]["label"]["type"] == "string"
    assert items["properties"]["content"]["type"] == "string"
