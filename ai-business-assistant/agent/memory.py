"""Conversation memory manager."""
from __future__ import annotations

from database.db import Database


class Memory:
    def __init__(self, db: Database, max_messages: int) -> None:
        self.db = db
        self.max_messages = max_messages

    def add_message(self, chat_id: str, role: str, content: str) -> None:
        self.db.insert(
            "INSERT INTO conversation_history (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, self.db.utc_now()),
        )

    def get_recent(self, chat_id: str) -> list[dict[str, str]]:
        rows = self.db.fetchall(
            """
            SELECT role, content FROM conversation_history
            WHERE chat_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (chat_id, self.max_messages),
        )
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
