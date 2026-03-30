"""Tests for LLM configuration loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.services.llm_config import LLMConfig, _resolve_env_vars

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_SAMPLE_YAML = textwrap.dedent("""\
    providers:
      openai:
        api_key: ${TEST_OPENAI_KEY}
      anthropic:
        api_key: ${TEST_ANTHROPIC_KEY}
    models:
      gpt4o:
        provider: openai
        model: gpt-4o
      gpt4o-mini:
        provider: openai
        model: gpt-4o-mini
      claude-sonnet:
        provider: anthropic
        model: claude-sonnet-4-6
      embedding:
        provider: openai
        model: text-embedding-3-small
    agent_models:
      resume_writer: gpt4o
      job_analyst: gpt4o-mini
      chat_agent: claude-sonnet
""")


@pytest.fixture
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set fake API keys for the test config."""
    monkeypatch.setenv("TEST_OPENAI_KEY", "sk-test-openai-key-123")
    monkeypatch.setenv("TEST_ANTHROPIC_KEY", "sk-test-anthropic-key-456")


@pytest.fixture
def config_path(tmp_path: Path, _env: None) -> Path:
    """Write the sample YAML to a temp file and return its path."""
    p = tmp_path / "llm.yaml"
    p.write_text(_SAMPLE_YAML)
    return p


@pytest.fixture
def llm_config(config_path: Path) -> LLMConfig:
    return LLMConfig(config_path)


# ---------------------------------------------------------------------------
# _resolve_env_vars unit tests
# ---------------------------------------------------------------------------


class TestResolveEnvVars:
    def test_string_substitution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FOO", "bar")
        assert _resolve_env_vars("prefix-${FOO}-suffix") == "prefix-bar-suffix"

    def test_nested_dict(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("A", "1")
        monkeypatch.setenv("B", "2")
        result = _resolve_env_vars({"x": "${A}", "y": {"z": "${B}"}})
        assert result == {"x": "1", "y": {"z": "2"}}

    def test_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("V", "val")
        assert _resolve_env_vars(["${V}", "literal"]) == ["val", "literal"]

    def test_non_string_passthrough(self) -> None:
        assert _resolve_env_vars(42) == 42
        assert _resolve_env_vars(None) is None
        assert _resolve_env_vars(True) is True

    def test_missing_env_var_raises(self) -> None:
        with pytest.raises(OSError, match="MISSING_VAR.*not set"):
            _resolve_env_vars("${MISSING_VAR}")


# ---------------------------------------------------------------------------
# LLMConfig loading tests
# ---------------------------------------------------------------------------


class TestLLMConfigLoading:
    def test_load_resolves_env_vars(self, llm_config: LLMConfig) -> None:
        assert llm_config.raw_config["providers"]["openai"]["api_key"] == "sk-test-openai-key-123"
        assert llm_config.raw_config["providers"]["anthropic"]["api_key"] == "sk-test-anthropic-key-456"

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            LLMConfig(tmp_path / "nonexistent.yaml")

    def test_missing_env_var_at_load(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("key: ${DOES_NOT_EXIST_XYZ}")
        with pytest.raises(OSError, match="DOES_NOT_EXIST_XYZ"):
            LLMConfig(p)


# ---------------------------------------------------------------------------
# Model factory tests
# ---------------------------------------------------------------------------


class TestGetChatModel:
    def test_openai_model(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("resume_writer")
        assert isinstance(model, ChatOpenAI)
        assert isinstance(model, BaseChatModel)
        assert model.model_name == "gpt-4o"

    def test_openai_mini_model(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("job_analyst")
        assert isinstance(model, ChatOpenAI)
        assert model.model_name == "gpt-4o-mini"

    def test_anthropic_model(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("chat_agent")
        assert isinstance(model, ChatAnthropic)
        assert model.model == "claude-sonnet-4-6"

    def test_custom_temperature(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("resume_writer", temperature=0.2)
        assert isinstance(model, ChatOpenAI)
        assert model.temperature == pytest.approx(0.2)

    def test_streaming_default_true(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("resume_writer")
        assert model.streaming is True

    def test_streaming_disabled(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_chat_model("resume_writer", streaming=False)
        assert model.streaming is False

    def test_unknown_agent_raises(self, llm_config: LLMConfig) -> None:
        with pytest.raises(KeyError):
            llm_config.get_chat_model("nonexistent_agent")


class TestGetEmbeddingModel:
    def test_returns_openai_embeddings(self, llm_config: LLMConfig) -> None:
        model = llm_config.get_embedding_model()
        assert isinstance(model, OpenAIEmbeddings)
        assert model.model == "text-embedding-3-small"


class TestUnsupportedProvider:
    def test_unsupported_chat_provider(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KEY", "x")
        p = tmp_path / "llm.yaml"
        p.write_text(textwrap.dedent("""\
            providers:
              google:
                api_key: ${KEY}
            models:
              gemini:
                provider: google
                model: gemini-pro
            agent_models:
              test: gemini
        """))
        cfg = LLMConfig(p)
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            cfg.get_chat_model("test")

    def test_unsupported_embedding_provider(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KEY", "x")
        p = tmp_path / "llm.yaml"
        p.write_text(textwrap.dedent("""\
            providers:
              google:
                api_key: ${KEY}
            models:
              embedding:
                provider: google
                model: text-embedding-gecko
            agent_models: {}
        """))
        cfg = LLMConfig(p)
        with pytest.raises(ValueError, match="Unsupported embedding provider"):
            cfg.get_embedding_model()
