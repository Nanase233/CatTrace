"""固定帧率节拍器。

为什么必须限帧：Pi4 上 AI 管线只能跑 2~3fps，跟着摄像头 30fps 跑会直接卡死。
"""

from __future__ import annotations

import time
from collections import deque


class Ticker:
    """按固定 fps 节拍：本轮处理完就睡到下一个时间点。

    用法：
        t = Ticker(3)
        while ...:
            t.wait()      # 到点才继续
            do_work()
    """

    def __init__(self, fps: float, *, catch_up: bool = False) -> None:
        if fps <= 0:
            raise ValueError("fps 必须 > 0")
        self.fps = float(fps)
        self.interval = 1.0 / self.fps
        self.catch_up = catch_up
        self._next: float | None = None

    def wait(self) -> float:
        """睡到下一个节拍点，返回实际睡眠秒数（0 表示已经迟到，没睡）。"""
        now = time.monotonic()
        if self._next is None:
            self._next = now
        slept = 0.0
        if now < self._next:
            slept = self._next - now
            time.sleep(slept)
            now = time.monotonic()
        # 下一拍：正常情况加上 interval；迟到且不追帧时，从当前时间重新起算
        self._next += self.interval
        if self._next < now:
            if self.catch_up:
                missed = int((now - self._next) / self.interval) + 1
                self._next += missed * self.interval
            else:
                self._next = now + self.interval
        return slept

    def reset(self) -> None:
        self._next = None


class FrameRateMeter:
    """滑动窗口统计真实处理帧率，用来判断 Pi 扛不扛得住。"""

    def __init__(self, window: int = 30) -> None:
        self.window = window
        self._ts: deque[float] = deque(maxlen=window)

    def tick(self) -> None:
        self._ts.append(time.monotonic())

    @property
    def fps(self) -> float:
        if len(self._ts) < 2:
            return 0.0
        span = self._ts[-1] - self._ts[0]
        return 0.0 if span <= 0 else (len(self._ts) - 1) / span

    @property
    def count(self) -> int:
        return len(self._ts)

    def __str__(self) -> str:
        return f"{self.fps:.2f} fps (n={self.count})"
