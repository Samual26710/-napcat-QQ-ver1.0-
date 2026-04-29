from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class ScheduleStore:
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
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT,
                events TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                token TEXT NOT NULL,
                schedule_id INTEGER,
                name TEXT,
                last_sync TEXT,
                status TEXT
            )
            """
        )
        self._conn.commit()

    def save_schedule(self, owner: str, name: str, events: List[Dict[str, Any]]) -> int:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        payload = json.dumps(events, ensure_ascii=False)
        cur.execute("INSERT INTO schedules(owner, name, events) VALUES(?,?,?)", (owner, name, payload))
        self._conn.commit()
        return cur.lastrowid

    def list_schedules(self, owner: str) -> List[Dict[str, Any]]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT id, name, events FROM schedules WHERE owner = ? ORDER BY id DESC", (owner,))
        rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for sid, name, events_json in rows:
            try:
                events = json.loads(events_json)
            except Exception:
                events = []
            result.append({"id": sid, "name": name, "events": events})
        return result

    def get_events(self, owner: str) -> List[Dict[str, Any]]:
        # merge all schedules for owner
        items = self.list_schedules(owner)
        events: List[Dict[str, Any]] = []
        for it in items:
            events.extend(it.get("events", []))
        return events

    def get_schedule(self, schedule_id: int) -> Dict[str, Any] | None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT id, owner, name, events FROM schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        if not row:
            return None
        sid, owner, name, events_json = row
        try:
            events = json.loads(events_json)
        except Exception:
            events = []
        return {"id": sid, "owner": owner, "name": name, "events": events}

    def update_schedule_events(self, schedule_id: int, events: List[Dict[str, Any]]) -> bool:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        payload = json.dumps(events, ensure_ascii=False)
        cur.execute("UPDATE schedules SET events = ? WHERE id = ?", (payload, schedule_id))
        self._conn.commit()
        return cur.rowcount > 0

    def create_binding(self, owner: str, token: str, schedule_id: int | None, name: str | None, status: str | None) -> int:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute(
            "INSERT INTO bindings(owner, token, schedule_id, name, last_sync, status) VALUES(?,?,?,?,?,?)",
            (owner, token, schedule_id, name, None, status),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_bindings(self, owner: str) -> List[Dict[str, Any]]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT id, token, schedule_id, name, last_sync, status FROM bindings WHERE owner = ? ORDER BY id DESC", (owner,))
        rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for sid, token, sched_id, name, last_sync, status in rows:
            result.append({"id": sid, "token": token, "schedule_id": sched_id, "name": name, "last_sync": last_sync, "status": status})
        return result

    def list_all_bindings(self) -> List[Dict[str, Any]]:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT id, owner, token, schedule_id, name, last_sync, status FROM bindings ORDER BY id DESC")
        rows = cur.fetchall()
        result: List[Dict[str, Any]] = []
        for sid, owner, token, sched_id, name, last_sync, status in rows:
            result.append({"id": sid, "owner": owner, "token": token, "schedule_id": sched_id, "name": name, "last_sync": last_sync, "status": status})
        return result

    def delete_binding(self, binding_id: int, owner: str) -> bool:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT owner FROM bindings WHERE id = ?", (binding_id,))
        row = cur.fetchone()
        if not row or row[0] != owner:
            return False
        cur.execute("DELETE FROM bindings WHERE id = ?", (binding_id,))
        self._conn.commit()
        return True

    def update_binding(self, binding_id: int, schedule_id: int | None = None, last_sync: str | None = None, status: str | None = None) -> bool:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        updates = []
        params = []
        if schedule_id is not None:
            updates.append("schedule_id = ?")
            params.append(schedule_id)
        if last_sync is not None:
            updates.append("last_sync = ?")
            params.append(last_sync)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if not updates:
            return False
        params.append(binding_id)
        sql = f"UPDATE bindings SET {', '.join(updates)} WHERE id = ?"
        cur.execute(sql, tuple(params))
        self._conn.commit()
        return cur.rowcount > 0

    def get_schedule(self, schedule_id: int) -> Dict[str, Any] | None:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        cur.execute("SELECT id, owner, name, events FROM schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        if not row:
            return None
        sid, owner, name, events_json = row
        try:
            events = json.loads(events_json)
        except Exception:
            events = []
        return {"id": sid, "owner": owner, "name": name, "events": events}

    def delete_schedule(self, schedule_id: int, owner: str) -> bool:
        if not self._conn:
            self.init_db()
        cur = self._conn.cursor()
        # ensure owner matches
        cur.execute("SELECT owner FROM schedules WHERE id = ?", (schedule_id,))
        row = cur.fetchone()
        if not row:
            return False
        if row[0] != owner:
            return False
        cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        self._conn.commit()
        return True


__all__ = ["ScheduleStore"]
