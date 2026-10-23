"""SQLite 状态存储。

只存决策需要跨进程记住的东西：
- 上次投粮时间（6 小时去重靠它）
- 发过的事件（前端查历史、避免重复推送）

用标准库 sqlite3，不引依赖；表结构改动不频繁，不用 ORM。
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS action_events (
    event_id    TEXT PRIMARY KEY,
    emitted_at  TEXT NOT NULL,
    type        TEXT NOT NULL,
    track_id    TEXT,
    cat_id      TEXT,
    reason      TEXT NOT NULL,
    payload     TEXT NOT NULL,
    status      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_action_cat_type ON action_events(cat_id, type, emitted_at);
CREATE INDEX IF NOT EXISTS idx_action_track    ON action_events(track_id, emitted_at);

CREATE TABLE IF NOT EXISTS detection_events (
    event_id     TEXT PRIMARY KEY,
    emitted_at   TEXT NOT NULL,
    camera_id    TEXT NOT NULL,
    track_id     TEXT NOT NULL,
    cat_id       TEXT,
    decision     TEXT NOT NULL,
    neutered     INTEGER,
    payload      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feed_log (
    cat_id     TEXT PRIMARY KEY,
    last_feed  TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    """默认落 SQLite；:memory: 可用于测试。"""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- 写入 -------------------------------------------------------------
    def record_action(self, event) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO action_events VALUES (?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.emitted_at.isoformat(),
                event.type,
                event.track_id,
                event.cat_id,
                event.reason,
                json.dumps(event.payload, ensure_ascii=False),
                event.status,
            ),
        )
        if event.type == "FEED_DISPENSE" and event.status in ("queued", "executed") and event.cat_id:
            self.conn.execute(
                "INSERT OR REPLACE INTO feed_log VALUES (?,?)",
                (event.cat_id, event.emitted_at.isoformat()),
            )
        self.conn.commit()

    def record_detection(self, event) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO detection_events VALUES (?,?,?,?,?,?,?,?)",
            (
                event.event_id,
                event.emitted_at.isoformat(),
                event.camera_id,
                event.track_id,
                event.cat.cat_id,
                event.cat.decision,
                None if event.neutered.value is None else int(event.neutered.value),
                json.dumps(event.to_dict(), ensure_ascii=False),
            ),
        )
        self.conn.commit()

    # -- 查询 -------------------------------------------------------------
    def last_feed_at(self, cat_id: str) -> datetime | None:
        row = self.conn.execute("SELECT last_feed FROM feed_log WHERE cat_id = ?", (cat_id,)).fetchone()
        if not row:
            return None
        return datetime.fromisoformat(row["last_feed"])

    def last_action_at(self, track_id: str, action_type: str) -> datetime | None:
        row = self.conn.execute(
            "SELECT emitted_at FROM action_events WHERE track_id = ? AND type = ? "
            "ORDER BY emitted_at DESC LIMIT 1",
            (track_id, action_type),
        ).fetchone()
        return datetime.fromisoformat(row["emitted_at"]) if row else None

    def counts(self) -> dict:
        return {
            "action_events": self.conn.execute("SELECT COUNT(*) c FROM action_events").fetchone()["c"],
            "detection_events": self.conn.execute("SELECT COUNT(*) c FROM detection_events").fetchone()["c"],
            "feed_log": self.conn.execute("SELECT COUNT(*) c FROM feed_log").fetchone()["c"],
        }

    def close(self) -> None:
        self.conn.close()
