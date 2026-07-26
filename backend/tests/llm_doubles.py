"""Offline test doubles for the Anthropic SDK.

Responses are real anthropic.types.Message objects, so production code is
exercised against the same attribute shapes the SDK returns rather than
against a loose stand-in that would let a typo pass. Nothing in this module
opens a socket or reads ANTHROPIC_API_KEY.
"""

from typing import Any, Dict, List, Optional

import httpx
from anthropic.types import Message, TextBlock, ToolUseBlock, Usage

MOCK_MODEL = "claude-haiku-4-5-20251001"


def build_tool_use_message(tool_name: str, tool_input: Dict[str, Any]) -> Message:
    """Build the response Claude returns when a tool call is forced."""
    return Message(
        id="msg_test_tool_use",
        content=[
            ToolUseBlock(
                id="toolu_test", input=tool_input, name=tool_name, type="tool_use"
            )
        ],
        model=MOCK_MODEL,
        role="assistant",
        stop_reason="tool_use",
        type="message",
        usage=Usage(input_tokens=100, output_tokens=50),
    )


def build_truncated_tool_use_message(
    tool_name: str, tool_input: Dict[str, Any]
) -> Message:
    """Build the response Claude returns when max_tokens cuts off a tool call.

    The content still carries a matching tool_use block (Claude was mid-call
    when the token ceiling hit), but stop_reason is "max_tokens" instead of
    "tool_use", signalling the emitted input may be incomplete.
    """
    return Message(
        id="msg_test_truncated_tool_use",
        content=[
            ToolUseBlock(
                id="toolu_test", input=tool_input, name=tool_name, type="tool_use"
            )
        ],
        model=MOCK_MODEL,
        role="assistant",
        stop_reason="max_tokens",
        type="message",
        usage=Usage(input_tokens=100, output_tokens=4096),
    )


def build_text_only_message(text: str = "I cannot help with that.") -> Message:
    """Build a response with prose and no tool call at all."""
    return Message(
        id="msg_test_text",
        content=[TextBlock(text=text, type="text")],
        model=MOCK_MODEL,
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=Usage(input_tokens=100, output_tokens=10),
    )


def build_anthropic_error(error_class, status_code: int = 400):
    """Build a real SDK status error. These require httpx request/response objects."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return error_class(
        "simulated failure",
        response=httpx.Response(status_code, request=request),
        body=None,
    )


class FakeMessagesResource:
    """Stands in for client.messages. Records every request instead of sending it."""

    def __init__(
        self, response: Any = None, error: Optional[BaseException] = None
    ) -> None:
        self._response = response
        self._error = error
        self.calls: List[Dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class FakeAnthropicClient:
    """Stands in for anthropic.Anthropic."""

    def __init__(
        self, response: Any = None, error: Optional[BaseException] = None
    ) -> None:
        self.messages = FakeMessagesResource(response=response, error=error)
