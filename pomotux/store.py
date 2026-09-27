"""SQLite persistence (stdlib only) + JSON export/import for device sync."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


def _db_path() -> Path:
    p = Path.home() / ".local" / "share" / "pomotux"
    p.mkdir(parents=True, exist_ok=True)
    return p / "pomotux.db"


@dataclass
class Task:
    id: int
    title: str
    done: bool
    pomodoros: int


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or _db_path()
        self._db = sqlite3.connect(str(self.path))
        self._db.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        self._db.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(
          id INTEGER PRIMARY KEY, title TEXT NOT NULL,
          done INTEGER NOT NULL DEFAULT 0, pomodoros INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
          id INTEGER PRIMARY KEY, kind TEXT NOT NULL,
          started_at TEXT NOT NULL, duration_sec INTEGER NOT NULL,
          task_id INTEGER REFERENCES tasks(id));
        """)
        self._db.commit()

    # -- tasks ------------------------------------------------------------
    def add_task(self, title: str) -> Task:
        title = title.strip()
        if not title:
            raise ValueError("empty title")
        cur = self._db.execute(
            "INSERT INTO tasks(title, done, pomodoros, created_at) VALUES(?,?,0,?)",
            (title, 0, datetime.now().isoformat()))
        self._db.commit()
        return self.get_task(cur.lastrowid)

    def get_task(self, task_id: int) -> Task | None:
        r = self._db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return Task(r["id"], r["title"], bool(r["done"]), r["pomodoros"]) if r else None

    def list_tasks(self, include_done=False) -> list[Task]:
        q = "SELECT * FROM tasks" if include_done else "SELECT * FROM tasks WHERE done=0"
        rows = self._db.execute(q + " ORDER BY id").fetchall()
        return [Task(r["id"], r["title"], bool(r["done"]), r["pomodoros"]) for r in rows]

    def toggle_task(self, task_id: int):
        self._db.execute("UPDATE tasks SET done = 1 - done WHERE id=?", (task_id,))
        self._db.commit()

    def delete_task(self, task_id: int):
        self._db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self._db.commit()

    def bump_pomodoros(self, task_id: int):
        self._db.execute("UPDATE tasks SET pomodoros = pomodoros + 1 WHERE id=?", (task_id,))
        self._db.commit()

    # -- sessions ---------------------------------------------------------
    def log_session(self, kind: str, duration_sec: int, task_id: int | None):
        self._db.execute(
            "INSERT INTO sessions(kind, started_at, duration_sec, task_id) VALUES(?,?,?,?)",
            (kind, datetime.now().isoformat(), duration_sec, task_id))
        self._db.commit()

    def focus_last_7_days(self) -> list[int]:
        """Focus sessions per day, oldest→newest (7 values). Day boundaries local."""
        from datetime import date, timedelta
        days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
        out = []
        for d in days:
            r = self._db.execute(
                "SELECT COUNT(*) c FROM sessions WHERE kind='focus' AND date(started_at)=date(?)",
                (d.isoformat(),)).fetchone()
            out.append(r["c"])
        return out

    def today_focus(self) -> int:
        r = self._db.execute(
            "SELECT COUNT(*) c FROM sessions WHERE kind='focus' AND date(started_at)=date('now','localtime')"
        ).fetchone()
        return int(r["c"])

    def streak_days(self) -> int:
        """Consecutive days (incl. today/yesterday) with ≥1 focus session."""
        from datetime import date, timedelta
        streak, day = 0, date.today()
        # allow starting from yesterday if today empty
        if self._count_on(day) == 0:
            day -= timedelta(days=1)
        while self._count_on(day) > 0:
            streak += 1
            day -= timedelta(days=1)
        return streak

    def _count_on(self, day) -> int:
        r = self._db.execute(
            "SELECT COUNT(*) c FROM sessions WHERE kind='focus' AND date(started_at)=date(?)",
            (day.isoformat(),)).fetchone()
        return int(r["c"])

    # -- backup -----------------------------------------------------------
    def export_json(self, dest: Path) -> Path:
        tasks = [dict(r) for r in self._db.execute("SELECT * FROM tasks").fetchall()]
        sessions = [dict(r) for r in self._db.execute("SELECT * FROM sessions").fetchall()]
        dest.write_text(json.dumps({"app": "pomotux", "tasks": tasks,
                                    "sessions": sessions}, indent=2))
        return dest

    def import_json(self, src: Path):
        data = json.loads(src.read_text())
        if data.get("app") != "pomotux":
            raise ValueError("not a PomoTux backup")
        with self._db:
            self._db.execute("DELETE FROM sessions")
            self._db.execute("DELETE FROM tasks")
            for t in data.get("tasks", []):
                self._db.execute(
                    "INSERT INTO tasks(id,title,done,pomodoros,created_at) VALUES(?,?,?,?,?)",
                    (t["id"], t["title"], t["done"], t["pomodoros"], t["created_at"]))
            for s in data.get("sessions", []):
                self._db.execute(
                    "INSERT INTO sessions(id,kind,started_at,duration_sec,task_id) VALUES(?,?,?,?,?)",
                    (s["id"], s["kind"], s["started_at"], s["duration_sec"], s["task_id"]))
