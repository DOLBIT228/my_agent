"""Google Calendar integration helpers."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarService:
    def __init__(self, token_file: str = "token.json", credentials_file: str = "credentials.json") -> None:
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.service = self._build_service()

    def _build_service(self):
        creds = None
        try:
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        except FileNotFoundError:
            creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def list_events(self, max_results: int = 10) -> list[dict[str, Any]]:
        now = datetime.utcnow().isoformat() + "Z"
        events_result = (
            self.service.events()
            .list(calendarId="primary", timeMin=now, maxResults=max_results, singleEvents=True, orderBy="startTime")
            .execute()
        )
        return events_result.get("items", [])

    def create_event(self, summary: str, start: datetime, end: datetime, description: str = "") -> str:
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        }
        created = self.service.events().insert(calendarId="primary", body=event).execute()
        return created.get("id", "")

    def update_event(self, event_id: str, **updates: Any) -> None:
        event = self.service.events().get(calendarId="primary", eventId=event_id).execute()
        event.update(updates)
        self.service.events().update(calendarId="primary", eventId=event_id, body=event).execute()

    def delete_event(self, event_id: str) -> None:
        self.service.events().delete(calendarId="primary", eventId=event_id).execute()

    @staticmethod
    def parse_simple_time_window(hours: int = 1) -> tuple[datetime, datetime]:
        start = datetime.utcnow() + timedelta(hours=1)
        end = start + timedelta(hours=hours)
        return start, end
