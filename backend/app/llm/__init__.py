"""Claude integration for the backend.

Every Anthropic API call in this project is made through app.llm.client. Per
the token-cost discipline in AGENTS.md, the LLM is reserved for genuine
language synthesis: document parsing, storage, filtering, reordering, and
export are deterministic library code elsewhere in the backend.
"""

from .client import (
    API_KEY_ENVIRONMENT_VARIABLE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    ClaudeClient,
    build_cached_system_blocks,
    extract_tool_input,
)
from .errors import (
    LLMConfigurationError,
    LLMError,
    LLMRequestError,
    LLMResponseError,
)
from .prompts import REPORT_FIELD_SYSTEM_PROMPT, build_report_field_prompt
from .report_fields import (
    REPORT_FIELD_TOOL,
    REPORT_FIELD_TOOL_NAME,
    generate_report_fields,
)

__all__ = [
    "API_KEY_ENVIRONMENT_VARIABLE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_MODEL",
    "REPORT_FIELD_SYSTEM_PROMPT",
    "REPORT_FIELD_TOOL",
    "REPORT_FIELD_TOOL_NAME",
    "ClaudeClient",
    "LLMConfigurationError",
    "LLMError",
    "LLMRequestError",
    "LLMResponseError",
    "build_cached_system_blocks",
    "build_report_field_prompt",
    "extract_tool_input",
    "generate_report_fields",
]
