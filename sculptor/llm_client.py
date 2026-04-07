"""OpenAI-compatible LLM client for the sculptor agent."""

import logging
from typing import Any, Generator

from openai import OpenAI

log = logging.getLogger("sculptor.llm")


class LLMClient:
    """Thin wrapper around the OpenAI SDK for use with any compatible API.

    Supports OpenAI, Azure, Ollama (via compatible endpoint), vLLM,
    and any other OpenAI-compatible API.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """Send a chat completion request and return the response text."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature or self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        log.info("LLM request: model=%s, messages=%d, temp=%.1f", self.model, len(messages), kwargs["temperature"])
        log.debug("LLM base_url=%s", self.client.base_url)
        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content or ""
            log.info("LLM response: %d chars, finish_reason=%s", len(content), response.choices[0].finish_reason)
            log.debug("LLM response preview: %s", content[:200])
            return content
        except Exception as e:
            log.error("LLM API error: %s: %s", type(e).__name__, e)
            raise

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> Generator[str, None, None]:
        """Stream a chat completion, yielding text chunks."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Request a JSON response from the model."""
        return self.chat(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
