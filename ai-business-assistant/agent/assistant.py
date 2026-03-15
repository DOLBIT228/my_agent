"""Main assistant orchestration module."""
from __future__ import annotations

from pathlib import Path

from agent.executor import Executor
from agent.memory import Memory
from agent.planner import Planner
from llm.ollama_client import OllamaClient


class Assistant:
    def __init__(self, planner: Planner, executor: Executor, memory: Memory, ollama: OllamaClient) -> None:
        self.planner = planner
        self.executor = executor
        self.memory = memory
        self.ollama = ollama
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
            response = (
                "Поки не вдалося обробити запит локально. "
                "Спробуйте сформулювати коротше або розбити задачу на кроки."
            )

        if self._is_low_quality_response(response):
            response = (
                "Перепрошую, відповідь вийшла нечіткою. "
                "Уточніть, будь ласка, що саме потрібно: формат результату, обсяг або тему."
            )

        self.memory.add_message(chat_id, "assistant", response)
        return response
