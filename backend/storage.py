import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS histories (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS history_messages (
                    id TEXT PRIMARY KEY,
                    history_id TEXT NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS history_assessments (
                    id TEXT PRIMARY KEY,
                    history_id TEXT NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
                    message_id TEXT NOT NULL REFERENCES history_messages(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS llm_calls (
                    id TEXT PRIMARY KEY,
                    history_id TEXT NOT NULL REFERENCES histories(id) ON DELETE CASCADE,
                    message_id TEXT NOT NULL REFERENCES history_messages(id) ON DELETE CASCADE,
                    kind TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def ensure_history(self, history_id: str, title: str) -> dict[str, Any]:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO histories (id, title, notes, created_at, updated_at)
                VALUES (?, ?, '', ?, ?)
                ON CONFLICT(id) DO UPDATE SET title = excluded.title
                """,
                (history_id, title, now, now),
            )
        return self.get_history(history_id)

    def get_history(self, history_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM histories WHERE id = ?", (history_id,)).fetchone()
        if row is None:
            raise KeyError(history_id)
        return dict(row)

    def get_messages(self, history_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM history_messages WHERE history_id = ? ORDER BY created_at ASC",
                (history_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def add_message(self, history_id: str, role: str, content: str) -> dict[str, Any]:
        now = utc_now()
        message_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO history_messages (id, history_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (message_id, history_id, role, content, now),
            )
            conn.execute("UPDATE histories SET updated_at = ? WHERE id = ?", (now, history_id))
        return {"id": message_id, "history_id": history_id, "role": role, "content": content, "created_at": now}

    def add_assessments(self, history_id: str, message_id: str, assessments: dict[str, str]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO history_assessments (id, history_id, message_id, kind, content, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (str(uuid.uuid4()), history_id, message_id, kind, content, now)
                    for kind, content in assessments.items()
                ],
            )

    def add_llm_calls(self, history_id: str, message_id: str, calls: list[dict[str, Any]]) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO llm_calls (id, history_id, message_id, kind, request_json, response, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(uuid.uuid4()),
                        history_id,
                        message_id,
                        call["kind"],
                        json.dumps(call["request"], ensure_ascii=True, indent=2),
                        call["response"],
                        now,
                    )
                    for call in calls
                ],
            )

    def update_notes(self, history_id: str, notes: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE histories SET notes = ?, updated_at = ? WHERE id = ?",
                (notes, utc_now(), history_id),
            )

    def dump_history(self, history_id: str) -> dict[str, Any]:
        history = self.get_history(history_id)
        messages = self.get_messages(history_id)
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT kind, content, created_at
                FROM history_assessments
                WHERE history_id = ?
                ORDER BY created_at ASC
                """,
                (history_id,),
            ).fetchall()
            call_rows = conn.execute(
                """
                SELECT id, message_id, kind, request_json, response, created_at
                FROM llm_calls
                WHERE history_id = ?
                ORDER BY created_at ASC
                """,
                (history_id,),
            ).fetchall()
        return {
            "history": history,
            "messages": messages,
            "assessments": [dict(row) for row in rows],
            "llm_calls": [dict(row) for row in call_rows],
        }
