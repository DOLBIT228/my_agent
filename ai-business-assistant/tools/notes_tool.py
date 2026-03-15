"""Notes tool."""
from __future__ import annotations

from database.db import Database


class NotesTool:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_note(self, content: str) -> int:
        return self.db.insert(
            "INSERT INTO notes (content, created_at) VALUES (?, ?)",
            (content, self.db.utc_now()),
        )

    def list_notes(self, limit: int = 20) -> list[dict]:
        return self.db.fetchall(
            "SELECT id, content, created_at FROM notes ORDER BY id DESC LIMIT ?",
            (limit,),
        )
