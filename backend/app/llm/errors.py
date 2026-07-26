class LLMError(Exception):
    """Base class for every failure raised by the app.llm package."""


class LLMConfigurationError(LLMError):
    """Raised when required LLM configuration is missing or blank."""


class LLMRequestError(LLMError):
    """Raised when the Anthropic API call itself fails."""


class LLMResponseError(LLMError):
    """Raised when the Anthropic API returns a response we cannot use."""
