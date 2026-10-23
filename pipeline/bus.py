"""极简事件总线。

现在只有两种消费方（JSONL 落盘 + 内存列表），不做过度设计；
等接网页/小程序时再加订阅者，接口不用改。
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from catvision_contracts import ActionEvent, DetectionEvent

Handler = Callable[[Any], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: list[Handler] = []
        self.detections: list[DetectionEvent] = []
        self.actions: list[ActionEvent] = []
        self._jsonl = None

    # -- 订阅 -------------------------------------------------------------
    def subscribe(self, handler: Handler) -> None:
        self._subs.append(handler)

    def to_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._jsonl = p.open("w", encoding="utf-8")

    # -- 发布 -------------------------------------------------------------
    def publish(self, event) -> None:
        if isinstance(event, DetectionEvent):
            self.detections.append(event)
        elif isinstance(event, ActionEvent):
            self.actions.append(event)
        if self._jsonl is not None:
            self._jsonl.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
            self._jsonl.flush()
        for h in self._subs:
            h(event)

    def close(self) -> None:
        if self._jsonl is not None:
            self._jsonl.close()
            self._jsonl = None

    def __enter__(self) -> EventBus:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
