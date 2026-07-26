import anthropic
import httpx
import pytest
from llm_doubles import (
    FakeAnthropicClient,
    build_anthropic_error,
    build_text_only_message,
    build_tool_use_message,
)

from app.llm.client import (
    API_KEY_ENVIRONMENT_VARIABLE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    ClaudeClient,
    build_cached_system_blocks,
    extract_tool_input,
)
from app.llm.errors import LLMConfigurationError, LLMRequestError, LLMResponseError

TOOL = {"name": "demo_tool", "description": "d", "input_schema": {"type": "object"}}


def test_default_model_is_the_cheapest_capable_model():
    assert DEFAULT_MODEL == "claude-haiku-4-5-20251001"


def test_build_cached_system_blocks_marks_the_block_ephemeral():
    blocks = build_cached_system_blocks("instructions")

    assert blocks == [
        {
            "type": "text",
            "text": "instructions",
            "cache_control": {"type": "ephemeral"},
        }
    ]


def test_request_tool_call_sends_model_system_cache_and_forced_tool():
    api_client = FakeAnthropicClient(
        response=build_tool_use_message("demo_tool", {"ok": True})
    )
    client = ClaudeClient(api_client=api_client)

    result = client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert result == {"ok": True}
    request = api_client.messages.calls[0]
    assert request["model"] == DEFAULT_MODEL
    assert request["max_tokens"] == DEFAULT_MAX_TOKENS
    assert request["system"][0]["text"] == "sys"
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["tools"] == [TOOL]
    assert request["tool_choice"] == {"type": "tool", "name": "demo_tool"}
    assert request["messages"] == [{"role": "user", "content": "user"}]


def test_model_can_be_overridden():
    api_client = FakeAnthropicClient(response=build_tool_use_message("demo_tool", {}))
    client = ClaudeClient(api_client=api_client, model="claude-sonnet-4-6")

    client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert client.model == "claude-sonnet-4-6"
    assert api_client.messages.calls[0]["model"] == "claude-sonnet-4-6"


@pytest.mark.parametrize(
    "error_class",
    [
        anthropic.AuthenticationError,
        anthropic.RateLimitError,
        anthropic.BadRequestError,
    ],
)
def test_api_errors_become_llm_request_error(error_class):
    error = build_anthropic_error(error_class)
    client = ClaudeClient(api_client=FakeAnthropicClient(error=error))

    with pytest.raises(LLMRequestError) as error_info:
        client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert error_info.value.__cause__ is error


def test_connection_errors_become_llm_request_error():
    error = anthropic.APIConnectionError(
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    )
    client = ClaudeClient(api_client=FakeAnthropicClient(error=error))

    with pytest.raises(LLMRequestError) as error_info:
        client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert error_info.value.__cause__ is error


def test_missing_api_key_raises_configuration_error(monkeypatch):
    monkeypatch.delenv(API_KEY_ENVIRONMENT_VARIABLE, raising=False)
    client = ClaudeClient()

    with pytest.raises(LLMConfigurationError) as error_info:
        client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert API_KEY_ENVIRONMENT_VARIABLE in str(error_info.value)


def test_blank_api_key_raises_configuration_error(monkeypatch):
    monkeypatch.setenv(API_KEY_ENVIRONMENT_VARIABLE, "   ")

    with pytest.raises(LLMConfigurationError):
        ClaudeClient().request_tool_call("sys", "user", TOOL, "demo_tool")


def test_api_key_is_never_included_in_the_raised_error(monkeypatch):
    monkeypatch.setenv(API_KEY_ENVIRONMENT_VARIABLE, "sk-ant-secret-value")
    api_client = FakeAnthropicClient(
        error=build_anthropic_error(anthropic.AuthenticationError, 401)
    )
    client = ClaudeClient(api_client=api_client)

    with pytest.raises(LLMRequestError) as error_info:
        client.request_tool_call("sys", "user", TOOL, "demo_tool")

    assert "sk-ant-secret-value" not in str(error_info.value)


def test_client_builds_a_real_sdk_client_from_the_environment(monkeypatch):
    monkeypatch.setenv(API_KEY_ENVIRONMENT_VARIABLE, "sk-ant-from-env")
    captured = {}

    class RecordingAnthropic:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.messages = FakeAnthropicClient(
                response=build_tool_use_message("demo_tool", {"ok": 1})
            ).messages

    monkeypatch.setattr("app.llm.client.anthropic.Anthropic", RecordingAnthropic)

    result = ClaudeClient().request_tool_call("sys", "user", TOOL, "demo_tool")

    assert captured["api_key"] == "sk-ant-from-env"
    assert result == {"ok": 1}


def test_extract_tool_input_rejects_a_text_only_response():
    with pytest.raises(LLMResponseError):
        extract_tool_input(build_text_only_message(), "demo_tool")


def test_extract_tool_input_rejects_a_different_tool_name():
    with pytest.raises(LLMResponseError):
        extract_tool_input(build_tool_use_message("other_tool", {}), "demo_tool")


def test_extract_tool_input_rejects_a_non_object_input():
    message = build_tool_use_message("demo_tool", {})
    message.content[0].input = ["not", "an", "object"]

    with pytest.raises(LLMResponseError):
        extract_tool_input(message, "demo_tool")
