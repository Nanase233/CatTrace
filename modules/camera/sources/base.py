"""FrameSource 基类。

约定：
- open() 之后 width/height 必须可用
- read() 返回 PIL.Image（RGB）或 None（源结束/读失败）
- read() 永远不抛网络异常，出错返回 None，由上层计入失败率
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from PIL import Image

from ..source import SourceSpec


class FrameSource(ABC):
    kind: str = "unknown"

    def __init__(self, spec: SourceSpec, **opts: Any) -> None:
        self.spec = spec
        self.uri = spec.uri
        self.opts = opts
        self.width = int(opts.get("width", 640))
        self.height = int(opts.get("height", 480))
        self._opened = False
        self.frames_read = 0
        self.frames_failed = 0
        # 源的正常结束（视频读完 / 图片目录读完）不是故障，子类读尽时置 True。
        # 区分这两件事很重要：不然 stats 里的 dropped 会一直骗人。
        self.at_eof = False

    # -- 生命周期 ---------------------------------------------------------
    @abstractmethod
    def _open(self) -> None: ...

    @abstractmethod
    def _read(self) -> Image.Image | None: ...

    def _close(self) -> None:
        """可选钩子：默认什么都不做，需要释放资源的子类覆盖它。"""
        return None

    def open(self) -> FrameSource:
        self._open()
        self._opened = True
        return self

    def read(self) -> Image.Image | None:
        if not self._opened:
            raise RuntimeError("read() 之前必须先 open()")
        try:
            img = self._read()
        except Exception:
            if not self.at_eof:
                self.frames_failed += 1
            return None
        if img is None:
            if not self.at_eof:
                self.frames_failed += 1
            return None
        self.frames_read += 1
        self.width, self.height = img.size
        return img

    def close(self) -> None:
        if self._opened:
            self._close()
            self._opened = False

    def __enter__(self) -> FrameSource:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- 元信息 -----------------------------------------------------------
    def source_info(self):
        return self.spec.to_source_info()

    def stats(self) -> dict:
        return {
            "kind": self.kind,
            "uri": self.uri,
            "width": self.width,
            "height": self.height,
            "frames_read": self.frames_read,
            "frames_failed": self.frames_failed,
        }

    # -- 给子类的小工具 ---------------------------------------------------
    @staticmethod
    def _sleep_to_fps(interval: float, last: float) -> float:
        now = time.monotonic()
        gap = now - last
        if gap < interval:
            time.sleep(interval - gap)
        return time.monotonic()
