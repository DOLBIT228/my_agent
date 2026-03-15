"""Intent planner for routing requests to tools."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Plan:
    intent: str
    payload: dict
    use_fallback: bool = False


class Planner:
    def create_plan(self, text: str) -> Plan:
        low = text.lower()
        if low.startswith("add task:") or low.startswith("додай задачу:"):
            return Plan("add_task", {"description": text.split(":", 1)[1].strip()})
        if "list tasks" in low or "my tasks" in low or "список задач" in low or "мої задачі" in low:
            return Plan("list_tasks", {})
        if low.startswith("complete task") or low.startswith("виконай задачу"):
            task_id = int("".join(ch for ch in low if ch.isdigit()) or "0")
            return Plan("complete_task", {"task_id": task_id})
        if low.startswith("remember:") or low.startswith("запам'ятай:") or low.startswith("запамятай:"):
            return Plan("add_note", {"content": text.split(":", 1)[1].strip()})
        if "list notes" in low or "список нотаток" in low:
            return Plan("list_notes", {})
        if "remind me" in low or "нагадай" in low:
            return Plan("set_reminder", {"raw": text})
        if "meeting" in low or "schedule" in low or "зустріч" in low or "розклад" in low:
            return Plan("calendar_create_or_list", {"raw": text})
        if low.startswith("search ") or low.startswith("пошук "):
            return Plan("search", {"query": text[7:].strip()})
        if low.startswith("python:"):
            return Plan("python", {"code": text.split(":", 1)[1].strip()})

        complex_prompt = any(
            k in low
            for k in ["strategy", "analyze", "investor memo", "deep research", "стратег", "проаналізуй", "глибоке дослідження"]
        )
        return Plan("chat", {"text": text}, use_fallback=complex_prompt)
