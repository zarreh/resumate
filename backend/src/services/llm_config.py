"""LLM configuration loader — reads config/llm.yaml, resolves env vars,
and provides configured LangChain chat and embedding model instances."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from langchain_anthropic import ChatAnthropic
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

_ENV_VAR_RE = re.compile(r"\$\{([^}]+)}")


def _resolve_env_vars(value: Any) -> Any:  # noqa: ANN401
    """Recursively resolve ``${ENV_VAR}`` placeholders in a parsed YAML tree."""
    if isinstance(value, str):
        def _replacer(match: re.Match[str]) -> str:
            var = match.group(1)
            resolved = os.environ.get(var)
            if resolved is None:
                msg = (
                    f"Environment variable '{var}' is required by llm.yaml "
                    f"but is not set"
                )
                raise OSError(msg)
            return resolved

        return _ENV_VAR_RE.sub(_replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


class LLMConfig:
    """Loads ``config/llm.yaml``, resolves env-var placeholders, and acts as
    a factory for LangChain chat and embedding models."""

    def __init__(self, config_path: str | Path) -> None:
        self._config: dict[str, Any] = self._load_yaml(config_path)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(path: str | Path) -> dict[str, Any]:
        p = Path(path)
        if not p.exists():
            msg = f"LLM config file not found: {p}"
            raise FileNotFoundError(msg)
        with p.open() as f:
            raw: dict[str, Any] = yaml.safe_load(f)
        return _resolve_env_vars(raw)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_chat_model(
        self,
        agent_name: str,
        *,
        temperature: float | None = None,
        streaming: bool = True,
    ) -> BaseChatModel:
        """Return the configured chat model for *agent_name*.

        Raises ``KeyError`` if the agent or the model key it references
        is not defined in the config.
        """
        model_key = self._config["agent_models"][agent_name]
        model_def: dict[str, Any] = self._config["models"][model_key]
        provider = model_def["provider"]
        model_name = model_def["model"]
        api_key = self._config["providers"][provider]["api_key"]

        kwargs: dict[str, Any] = {"model": model_name, "streaming": streaming}
        if temperature is not None:
            kwargs["temperature"] = temperature

        if provider == "openai":
            return ChatOpenAI(api_key=api_key, **kwargs)
        if provider == "anthropic":
            return ChatAnthropic(api_key=api_key, **kwargs)

        msg = f"Unsupported LLM provider: {provider}"
        raise ValueError(msg)

    def get_embedding_model(self) -> Embeddings:
        """Return the configured embedding model."""
        model_def: dict[str, Any] = self._config["models"]["embedding"]
        provider = model_def["provider"]
        model_name = model_def["model"]
        api_key = self._config["providers"][provider]["api_key"]

        if provider == "openai":
            return OpenAIEmbeddings(model=model_name, api_key=api_key)

        msg = f"Unsupported embedding provider: {provider}"
        raise ValueError(msg)

    @property
    def raw_config(self) -> dict[str, Any]:
        """Expose the resolved config dict (useful for debugging)."""
        return self._config


@lru_cache(maxsize=1)
def get_llm_config() -> LLMConfig:
    """Return a cached singleton ``LLMConfig`` loaded from
    ``settings.llm_config_path``."""
    from src.core.config import settings

    return LLMConfig(settings.llm_config_path)
