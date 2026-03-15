"""Reminder scheduler built on APScheduler."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class ReminderScheduler:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def schedule(self, reminder_id: str, when: datetime, callback: Callable[[], None]) -> None:
        self.scheduler.add_job(callback, "date", run_date=when, id=reminder_id, replace_existing=True)
