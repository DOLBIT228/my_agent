"""Reminder tool backed by APScheduler and SQLite."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Awaitable, Callable

from database.db import Database
from scheduler.reminders import ReminderScheduler


class ReminderTool:
    def __init__(self, db: Database, scheduler: ReminderScheduler) -> None:
        self.db = db
        self.scheduler = scheduler

    def parse_relative_time(self, text: str) -> datetime | None:
        match = re.search(r"in\s+(\d+)\s+(minute|minutes|hour|hours)", text.lower())
        if not match:
            return None
        amount = int(match.group(1))
        unit = match.group(2)
        delta = timedelta(minutes=amount) if "minute" in unit else timedelta(hours=amount)
        return datetime.utcnow() + delta

    def add_reminder(
        self,
        chat_id: str,
        message: str,
        remind_at: datetime,
        send_callback: Callable[[str, str], Awaitable[None]],
    ) -> int:
        reminder_id = self.db.insert(
            "INSERT INTO reminders (chat_id, message, remind_at, created_at, sent) VALUES (?, ?, ?, ?, 0)",
            (chat_id, message, remind_at.isoformat(), self.db.utc_now()),
        )

        async def _send() -> None:
            await send_callback(chat_id, f"⏰ Reminder: {message}")
            self.db.execute("UPDATE reminders SET sent = 1 WHERE id = ?", (reminder_id,))

        self.scheduler.schedule(str(reminder_id), remind_at, lambda: __import__("asyncio").create_task(_send()))
        return reminder_id
