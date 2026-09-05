"""Provider-agnostic LLM abstraction for SuperApp."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from superapp.config import settings


class LLMProvider(ABC):
    """Base interface for model providers."""

    name: str = "base"

    @abstractmethod
    async def chat(self, messages: list[dict[str, str]], *, model: str | None = None, response_format: str | None = None) -> dict[str, Any]:
        """Return a dict-like LLM response."""

    @abstractmethod
    async def embed(self, text: str | list[str], *, model: str | None = None) -> list[float] | list[list[float]]:
        """Return embedding vectors."""


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, host: str | None = None):
        self.host = host or settings.ollama_host
        try:
            import ollama

            self._client = ollama.AsyncClient(host=self.host)
        except Exception as exc:  # pragma: no cover - env issue
            self._client = None
            self._init_error = exc

    async def chat(self, messages: list[dict[str, str]], *, model: str | None = None, response_format: str | None = None) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError(f"Ollama client is not available: {self._init_error}")
        kwargs: dict[str, Any] = {
            "model": model or settings.ollama_reasoning_model,
            "messages": messages,
        }
        if response_format:
            kwargs["format"] = response_format
        response = await self._client.chat(**kwargs)
        usage = getattr(response, "get", lambda *_: {}) ("prompt_eval_count", 0)
        response["usage"] = {
            "prompt_tokens": response.get("prompt_eval_count", usage or 0),
            "completion_tokens": response.get("eval_count", 0),
        }
        return response

    async def embed(self, text: str | list[str], *, model: str | None = None) -> list[float] | list[list[float]]:
        if self._client is None:
            raise RuntimeError(f"Ollama client is not available: {self._init_error}")
        return await self._client.embed(model=model or settings.ollama_embedding_model, input=text)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.openai_api_key
        self._client = None
        if self.api_key:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                self._init_error = exc
            else:
                self._init_error = None
        else:
            self._init_error = RuntimeError("OPENAI_API_KEY is missing")

    async def chat(self, messages: list[dict[str, str]], *, model: str | None = None, response_format: str | None = None) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError(f"OpenAI client is not available: {self._init_error}")
        request: dict[str, Any] = {
            "model": model or settings.openai_mid_model,
            "messages": messages,
        }
        if response_format:
            request["response_format"] = {"type": "json_object"}
        response = await self._client.chat.completions.create(**request)
        content = response.choices[0].message.content or "{}"
        usage = response.usage.model_dump() if response.usage else {}
        return {"message": {"content": content}, "usage": usage}

    async def embed(self, text: str | list[str], *, model: str | None = None) -> list[float] | list[list[float]]:
        if self._client is None:
            raise RuntimeError(f"OpenAI client is not available: {self._init_error}")
        input_value = text if isinstance(text, list) else [text]
        response = await self._client.embeddings.create(model=model or settings.openai_mid_model, input=input_value)
        return [item.embedding for item in response.data]


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None
        if self.api_key:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover
                self._init_error = exc
            else:
                self._init_error = None
        else:
            self._init_error = RuntimeError("ANTHROPIC_API_KEY is missing")

    async def chat(self, messages: list[dict[str, str]], *, model: str | None = None, response_format: str | None = None) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError(f"Anthropic client is not available: {self._init_error}")
        system_prompt = "\n".join(msg["content"] for msg in messages if msg.get("role") == "system")
        user_messages = [msg for msg in messages if msg.get("role") != "system"]
        response = await self._client.messages.create(
            model=model or settings.anthropic_mid_model,
            max_tokens=2048,
            system=system_prompt,
            messages=user_messages,
        )
        content = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                content += block.text
        usage = getattr(response, "usage", None)
        return {
            "message": {"content": content or "{}"},
            "usage": {
                "input_tokens": getattr(usage, "input_tokens", 0),
                "output_tokens": getattr(usage, "output_tokens", 0),
            },
        }

    async def embed(self, text: str | list[str], *, model: str | None = None) -> list[float] | list[list[float]]:
        raise NotImplementedError("Anthropic embeddings are not implemented in this MVP adapter.")


def get_llm_provider() -> LLMProvider:
    provider_name = settings.llm_provider.lower()
    if provider_name == "anthropic":
        return AnthropicProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    return OllamaProvider()
