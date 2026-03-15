"""Optional OpenAI fallback for difficult requests."""
from __future__ import annotations

from openai import OpenAI


class OpenAIFallback:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, messages: list[dict[str, str]]) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return completion.choices[0].message.content or ""
