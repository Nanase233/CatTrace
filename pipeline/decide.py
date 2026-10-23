"""决策引擎：DetectionEvent -> ActionEvent。

规则（全部是配置项，禁止硬编码在模型里）：

投粮 FEED_DISPENSE：
  1. 猫脸 matched 且 similarity >= 0.80
  2. 画面里只有一只猫（concurrent_tracks == 1）
  3. 距上次给这只猫投粮 > 6 小时
  4. 同一 track_id 10 秒防抖
  5. 默认 dry-run：事件照常入队（status=queued），但 payload.dry_run=true，
     执行端看到 dry_run 就不开电机。prototype 阶段不允许真投粮。

TNR_TASK_CREATED：
  1. 明确判为未绝育（neutered.value is False）
  2. confidence >= 0.80
  3. 同一 track 10 秒防抖（真实跑要按天去重，接志愿者系统时再改）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from catvision_contracts import ActionEvent, DetectionEvent, new_id, utcnow

log = logging.getLogger("catvision.decide")


@dataclass
class DecisionConfig:
    feed_min_similarity: float = 0.80
    feed_cooldown_hours: float = 6.0
    feed_requires_single_cat: bool = True
    tnr_min_confidence: float = 0.80
    debounce_seconds: float = 10.0
    dry_run: bool = True
    portion_g: int = 30


class DecisionEngine:
    def __init__(self, config: DecisionConfig | None = None, store=None) -> None:
        self.cfg = config or DecisionConfig()
        self.store = store
        self._recent: dict[tuple[str, str, str], datetime] = {}

    # -- 主入口 -----------------------------------------------------------
    def decide(self, event: DetectionEvent) -> list[ActionEvent]:
        out: list[ActionEvent] = []
        out.extend(self._feed(event))
        out.extend(self._tnr(event))
        return out

    def _debounced(self, event: DetectionEvent, action_type: str, now: datetime) -> bool:
        key = (event.camera_id, event.track_id, action_type)
        last = self._recent.get(key)
        if last is not None and (now - last).total_seconds() < self.cfg.debounce_seconds:
            return True
        if self.store is not None:
            try:
                last_db = self.store.last_action_at(event.track_id, action_type)
            except Exception:
                last_db = None
            if last_db is not None and (now - last_db).total_seconds() < self.cfg.debounce_seconds:
                self._recent[key] = last_db
                return True
        self._recent[key] = now
        return False

    # -- 投粮 -------------------------------------------------------------
    def _feed(self, event: DetectionEvent) -> list[ActionEvent]:
        cat = event.cat
        now = utcnow()
        reason_skip: str | None = None

        if cat.decision != "matched" or not cat.cat_id:
            return []
        if cat.similarity is None or cat.similarity < self.cfg.feed_min_similarity:
            reason_skip = f"similarity {cat.similarity} < {self.cfg.feed_min_similarity}"
        elif self.cfg.feed_requires_single_cat and event.evidence.concurrent_tracks > 1:
            reason_skip = f"画面内有 {event.evidence.concurrent_tracks} 只猫，不投粮"
        else:
            last = self._last_feed(cat.cat_id)
            if last is not None:
                waited = (now - last).total_seconds() / 3600.0
                if waited < self.cfg.feed_cooldown_hours:
                    reason_skip = f"距上次投粮 {waited:.2f}h < {self.cfg.feed_cooldown_hours}h"

        if reason_skip:
            log.info("跳过投粮：%s（track=%s cat=%s）", reason_skip, event.track_id, cat.cat_id)
            return []

        if self._debounced(event, "FEED_DISPENSE", now):
            log.info("跳过投粮：track %s 处于 10s 防抖窗口", event.track_id)
            return []

        # dry-run 的语义：决策照常做出、事件照常入队，只是执行端不开电机。
        # 这里必须保持 status="queued"，否则 6 小时冷却记不进数据库，
        # dry-run 期间的反复投粮就测不出来。
        payload = {
            "cat_id": cat.cat_id,
            "similarity": cat.similarity,
            "portion_g": self.cfg.portion_g,
            "dry_run": self.cfg.dry_run,
            "device": "gpio://servo0" if not self.cfg.dry_run else "dry-run",
        }
        return [
            ActionEvent(
                event_id=new_id("act"),
                emitted_at=now,
                type="FEED_DISPENSE",
                track_id=event.track_id,
                cat_id=cat.cat_id,
                reason=f"识别到已建档猫 {cat.cat_id}，similarity={cat.similarity}",
                payload=payload,
                status="queued",
            )
        ]

    def _last_feed(self, cat_id: str) -> datetime | None:
        if self.store is None:
            return None
        try:
            return self.store.last_feed_at(cat_id)
        except Exception:
            return None

    # -- TNR --------------------------------------------------------------
    def _tnr(self, event: DetectionEvent) -> list[ActionEvent]:
        n = event.neutered
        now = utcnow()
        if n.value is not False:
            return []
        if n.confidence is None or n.confidence < self.cfg.tnr_min_confidence:
            log.info("跳过 TNR：confidence %s < %s", n.confidence, self.cfg.tnr_min_confidence)
            return []
        if self._debounced(event, "TNR_TASK_CREATED", now):
            return []

        return [
            ActionEvent(
                event_id=new_id("act"),
                emitted_at=now,
                type="TNR_TASK_CREATED",
                track_id=event.track_id,
                cat_id=event.cat.cat_id,
                reason=f"未剪耳，疑似未绝育（confidence={n.confidence}）",
                payload={
                    "confidence": n.confidence,
                    "snapshot": event.evidence.best_frame_path,
                    "cat_id": event.cat.cat_id,
                },
                status="queued",
            )
        ]
