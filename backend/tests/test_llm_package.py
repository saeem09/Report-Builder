import importlib
import sys

import pytest
from llm_doubles import FakeAnthropicClient, build_tool_use_message

import app.llm as llm


def test_package_exposes_the_generation_entry_point():
    api_client = FakeAnthropicClient(
        response=build_tool_use_message(
            llm.REPORT_FIELD_TOOL_NAME,
            {"fields": [{"label": "Summary", "content": "Kickoff held."}]},
        )
    )
    client = llm.ClaudeClient(api_client=api_client)

    result = llm.generate_report_fields("Kickoff notes.", ["Summary"], client=client)

    assert result == {"Summary": "Kickoff held."}


def test_package_exposes_the_error_hierarchy():
    assert issubclass(llm.LLMConfigurationError, llm.LLMError)
    assert issubclass(llm.LLMRequestError, llm.LLMError)
    assert issubclass(llm.LLMResponseError, llm.LLMError)


def test_package_exposes_the_model_and_environment_constants():
    assert llm.DEFAULT_MODEL == "claude-haiku-4-5-20251001"
    assert llm.DEFAULT_MAX_TOKENS == 4096
    assert llm.API_KEY_ENVIRONMENT_VARIABLE == "ANTHROPIC_API_KEY"


def test_all_names_are_importable():
    for name in llm.__all__:
        assert hasattr(llm, name), name


def test_package_imports_without_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    for module_name in [name for name in sys.modules if name.startswith("app.llm")]:
        del sys.modules[module_name]

    reimported = importlib.import_module("app.llm")

    assert reimported.DEFAULT_MODEL == "claude-haiku-4-5-20251001"


def test_constructing_a_client_without_an_api_key_does_not_raise(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    client = llm.ClaudeClient()

    assert client.model == llm.DEFAULT_MODEL


def test_requesting_without_an_api_key_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(llm.LLMConfigurationError):
        llm.generate_report_fields("Kickoff notes.", ["Summary"])
