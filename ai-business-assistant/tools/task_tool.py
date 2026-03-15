"""Task management tool."""
from __future__ import annotations

from database.db import Database


class TaskTool:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add_task(self, description: str) -> int:
        return self.db.insert(
            "INSERT INTO tasks (description, completed, created_at) VALUES (?, 0, ?)",
            (description, self.db.utc_now()),
        )

    def list_tasks(self) -> list[dict]:
        return self.db.fetchall("SELECT id, description, completed, created_at FROM tasks ORDER BY id DESC")

    def complete_task(self, task_id: int) -> None:
        self.db.execute("UPDATE tasks SET completed = 1 WHERE id = ?", (task_id,))
