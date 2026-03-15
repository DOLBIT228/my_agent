"""Main assistant orchestration module."""
from __future__ import annotations

from pathlib import Path

from agent.config import settings
from agent.executor import Executor
from agent.memory import Memory
from agent.planner import Planner
from llm.ollama_client import OllamaClient


class Assistant:
    def __init__(self, planner: Planner, executor: Executor, memory: Memory, ollama: OllamaClient, openai_fallback=None) -> None:
        self.planner = planner
        self.executor = executor
        self.memory = memory
        self.ollama = ollama
        self.openai_fallback = openai_fallback
        self.system_prompt = Path("prompts/system_prompt.txt").read_text(encoding="utf-8")

    @staticmethod
    def _is_low_quality_response(response: str) -> bool:
        normalized = " ".join(response.lower().split())
        if not normalized:
            return True
        parts = [part.strip() for part in normalized.split(".") if part.strip()]
        if len(parts) >= 4 and len(set(parts)) <= max(1, len(parts) // 2):
            return True
        return any(phrase in normalized for phrase in ["я не має", "я може", "я допомігти"])

    async def handle_message(self, chat_id: str, text: str, send_callback) -> str:
        self.memory.add_message(chat_id, "user", text)
        plan = self.planner.create_plan(text)

        tool_output = await self.executor.execute(plan.intent, plan.payload, chat_id, send_callback)
        if tool_output:
            self.memory.add_message(chat_id, "assistant", tool_output)
            return tool_output

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.memory.get_recent(chat_id))

        response = ""
        try:
            response = self.ollama.chat(messages)
        except Exception:
            if settings.ENABLE_OPENAI_FALLBACK and self.openai_fallback:
                response = self.openai_fallback.chat(messages)
            else:
                response = "Не вдалося опрацювати запит локально. Спробуйте переформулювати його коротше."

        if plan.use_fallback and settings.ENABLE_OPENAI_FALLBACK and self.openai_fallback:
            response = self.openai_fallback.chat(messages)

        if "use cloud" in text.lower() and settings.ENABLE_OPENAI_FALLBACK and self.openai_fallback:
            response = self.openai_fallback.chat(messages)

        if self._is_low_quality_response(response):
            if settings.ENABLE_OPENAI_FALLBACK and self.openai_fallback:
                response = self.openai_fallback.chat(messages)
            else:
                response = (
                    "Перепрошую, відповідь вийшла некоректною. "
                    "Будь ласка, уточніть запит — і я відповім чітко українською."
                )

        self.memory.add_message(chat_id, "assistant", response)
        return response
