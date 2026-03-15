"""Calendar tool wrapper over Google Calendar service."""
from __future__ import annotations

from datetime import datetime, timedelta

from integrations.google_calendar import GoogleCalendarService


class CalendarTool:
    def __init__(self, service: GoogleCalendarService) -> None:
        self.service = service

    def list_events(self) -> list[dict]:
        return self.service.list_events()

    def create_event(self, summary: str, start: datetime, duration_minutes: int = 60) -> str:
        end = start + timedelta(minutes=duration_minutes)
        return self.service.create_event(summary=summary, start=start, end=end)

    def update_event(self, event_id: str, **updates: str) -> None:
        self.service.update_event(event_id, **updates)

    def delete_event(self, event_id: str) -> None:
        self.service.delete_event(event_id)
