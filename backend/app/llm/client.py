"""The only module in this repository that talks to the Anthropic API.

Everything else in the backend is deterministic library code. Per the
token-cost discipline in AGENTS.md, calls made here are reserved for genuine
language synthesis and default to the cheapest capable model.
"""

import os
from types import MappingProxyType
from typing import Any, Dict, List, Optional

import anthropic

from .errors import LLMConfigurationError, LLMRequestError, LLMResponseError

API_KEY_ENVIRONMENT_VARIABLE = "ANTHROPIC_API_KEY"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_TOKENS = 4096
CACHE_CONTROL_EPHEMERAL = MappingProxyType({"type": "ephemeral"})


def build_cached_system_blocks(system_prompt: str) -> List[Dict[str, Any]]:
    """Wrap a system prompt in a cacheable block.

    Anthropic prompt caching needs the system prompt sent as a block list with
    a cache_control marker, not as a bare string. A fresh dict is returned on
    every call so callers can never mutate CACHE_CONTROL_EPHEMERAL.
    """
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": dict(CACHE_CONTROL_EPHEMERAL),
        }
    ]


def extract_tool_input(message: Any, tool_name: str) -> Dict[str, Any]:
    """Return the input of the named tool call in a Claude response.

    The caller forces this tool via tool_choice, so a response without it means
    something went structurally wrong and is not recoverable here. A response
    that hit the max_tokens ceiling mid-tool-call is also rejected: the tool
    input Claude managed to emit before being cut off would otherwise be used
    as-is, and downstream reconciliation logic cannot distinguish a truncated
    entry from Claude legitimately having nothing to say for a field.
    """
    for block in getattr(message, "content", ()) or ():
        if getattr(block, "type", None) != "tool_use":
            continue
        if getattr(block, "name", None) != tool_name:
            continue
        tool_input = getattr(block, "input", None)
        if not isinstance(tool_input, dict):
            raise LLMResponseError(
                "Claude returned a {0!r} tool call with a non-object input.".format(
                    tool_name
                )
            )
        if getattr(message, "stop_reason", None) == "max_tokens":
            raise LLMResponseError(
                "Claude's response was truncated by the max_tokens limit "
                "before the {0!r} tool call finished.".format(tool_name)
            )
        return tool_input
    raise LLMResponseError(
        "Claude did not return the required {0!r} tool call.".format(tool_name)
    )


class ClaudeClient:
    """A thin, testable wrapper around the Anthropic Messages API.

    api_client is the seam the test suite uses: pass anything exposing
    .messages.create(**kwargs) and no network call is made. When it is None,
    a real anthropic.Anthropic is built lazily on the first request, so
    importing this module and constructing a client both work without
    ANTHROPIC_API_KEY set.
    """

    def __init__(
        self,
        api_client: Optional[Any] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_client = api_client
        self._model = model
        self._max_tokens = max_tokens

    @property
    def model(self) -> str:
        return self._model

    def _resolve_api_client(self) -> Any:
        if self._api_client is not None:
            return self._api_client
        api_key = os.environ.get(API_KEY_ENVIRONMENT_VARIABLE, "").strip()
        if not api_key:
            raise LLMConfigurationError(
                "The {0} environment variable is not set. Set it before "
                "requesting AI-generated content.".format(
                    API_KEY_ENVIRONMENT_VARIABLE
                )
            )
        self._api_client = anthropic.Anthropic(api_key=api_key)
        return self._api_client

    def request_tool_call(
        self,
        system_prompt: str,
        user_prompt: str,
        tool: Dict[str, Any],
        tool_name: str,
    ) -> Dict[str, Any]:
        """Send one request that forces tool_name and return its input dict.

        Forcing the tool is how structured output is obtained: parsing free-form
        prose would be unreliable. The error message deliberately names only the
        exception class, so neither the API key nor the request body can leak
        into a message that may be shown to a user or written to a log.
        """
        api_client = self._resolve_api_client()
        try:
            message = api_client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=build_cached_system_blocks(system_prompt),
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.AnthropicError as error:
            raise LLMRequestError(
                "The request to Claude failed: {0}".format(type(error).__name__)
            ) from error
        return extract_tool_input(message, tool_name)
