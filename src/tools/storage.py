import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class SessionStorage:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        path = Path(self.db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_key TEXT PRIMARY KEY,
                messages TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS personas (
                session_key TEXT PRIMARY KEY,
                persona TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def load_all(self) -> Dict[str, List[Dict[str, str]]]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT session_key, messages FROM sessions")
        rows = cur.fetchall()
        result: Dict[str, List[Dict[str, str]]] = {}
        for key, messages_json in rows:
            try:
                msgs = json.loads(messages_json)
                if isinstance(msgs, list):
                    result[key] = msgs
            except Exception:
                continue
        return result

    def load_session(self, session_key: str) -> List[Dict[str, str]]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT messages FROM sessions WHERE session_key = ?", (session_key,))
        row = cur.fetchone()
        if not row:
            return []
        try:
            return json.loads(row[0])
        except Exception:
            return []

    def save_session(self, session_key: str, messages: List[Dict[str, str]]) -> None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        payload = json.dumps(messages, ensure_ascii=False)
        cur.execute(
            "INSERT INTO sessions(session_key, messages) VALUES(?, ?)"
            " ON CONFLICT(session_key) DO UPDATE SET messages=excluded.messages",
            (session_key, payload),
        )
        self._conn.commit()

    def delete_session(self, session_key: str) -> None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("DELETE FROM sessions WHERE session_key = ?", (session_key,))
        self._conn.commit()

    def clear_all(self) -> None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("DELETE FROM sessions")
        self._conn.commit()

    # Persona persistence helpers
    def save_persona(self, session_key: str, persona: str) -> None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO personas(session_key, persona) VALUES(?, ?)"
            " ON CONFLICT(session_key) DO UPDATE SET persona=excluded.persona",
            (session_key, persona),
        )
        self._conn.commit()

    def load_persona(self, session_key: str) -> str | None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT persona FROM personas WHERE session_key = ?", (session_key,))
        row = cur.fetchone()
        if not row:
            return None
        return row[0]

    def delete_persona(self, session_key: str) -> None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("DELETE FROM personas WHERE session_key = ?", (session_key,))
        self._conn.commit()

    def load_all_personas(self) -> dict[str, str]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT session_key, persona FROM personas")
        rows = cur.fetchall()
        return {k: v for k, v in rows}


__all__ = ["SessionStorage"]
