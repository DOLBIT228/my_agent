"""Executes plans by invoking tool methods."""
from __future__ import annotations

import re
from datetime import datetime

from tools.calendar_tool import CalendarTool
from tools.notes_tool import NotesTool
from tools.python_exec_tool import PythonExecTool
from tools.reminder_tool import ReminderTool
from tools.search_tool import SearchTool
from tools.task_tool import TaskTool


class Executor:
    def __init__(
        self,
        task_tool: TaskTool,
        notes_tool: NotesTool,
        reminder_tool: ReminderTool,
        calendar_tool: CalendarTool | None,
        search_tool: SearchTool,
        python_tool: PythonExecTool,
    ) -> None:
        self.task_tool = task_tool
        self.notes_tool = notes_tool
        self.reminder_tool = reminder_tool
        self.calendar_tool = calendar_tool
        self.search_tool = search_tool
        self.python_tool = python_tool

    async def execute(self, plan_intent: str, payload: dict, chat_id: str, send_callback):
        if plan_intent == "add_task":
            task_id = self.task_tool.add_task(payload["description"])
            return f"✅ Task #{task_id} added."

        if plan_intent == "list_tasks":
            tasks = self.task_tool.list_tasks()
            if not tasks:
                return "No tasks yet."
            return "\n".join([f"- [{ 'x' if t['completed'] else ' '}] {t['id']}: {t['description']}" for t in tasks])

        if plan_intent == "complete_task":
            self.task_tool.complete_task(payload["task_id"])
            return f"✅ Task #{payload['task_id']} marked complete."

        if plan_intent == "add_note":
            note_id = self.notes_tool.add_note(payload["content"])
            return f"📝 Note #{note_id} saved."

        if plan_intent == "list_notes":
            notes = self.notes_tool.list_notes()
            return "\n".join([f"- {n['id']}: {n['content']}" for n in notes]) if notes else "No notes found."

        if plan_intent == "set_reminder":
            remind_at = self.reminder_tool.parse_relative_time(payload["raw"])
            if not remind_at:
                return "Please use format like: Remind me in 30 minutes to send email"
            msg_match = re.search(r"to\s+(.+)$", payload["raw"], re.IGNORECASE)
            reminder_msg = msg_match.group(1) if msg_match else payload["raw"]
            reminder_id = self.reminder_tool.add_reminder(chat_id, reminder_msg, remind_at, send_callback)
            return f"⏰ Reminder #{reminder_id} set for {remind_at.isoformat()} UTC"

        if plan_intent == "calendar_create_or_list":
            if not self.calendar_tool:
                return "Google Calendar integration is disabled."
            if "today" in payload["raw"].lower() or "what meetings" in payload["raw"].lower():
                events = self.calendar_tool.list_events()
                if not events:
                    return "No upcoming meetings found."
                return "\n".join([f"- {e.get('summary', '(no title)')} @ {e.get('start', {}).get('dateTime', 'N/A')}" for e in events])
            start = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            event_id = self.calendar_tool.create_event(summary=payload["raw"], start=start)
            return f"📅 Calendar event created (id={event_id})."

        if plan_intent == "search":
            results = self.search_tool.search(payload["query"])
            if not results:
                return "No search results found."
            return "\n".join([f"- {r.get('title')}: {r.get('href')}" for r in results[:5]])

        if plan_intent == "python":
            return self.python_tool.run(payload["code"])

        return ""
