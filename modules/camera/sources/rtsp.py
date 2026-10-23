"""RTSP 网络摄像头源（ffmpeg 拉流）。

选型要求（摄像头模块负责）：支持 RTSP/HTTP 拉流 + 红外夜视。
- 优先 H.264 主码流，否则 ffmpeg 解码开销会吃满 Pi4
- 必须设 -rtsp_transport tcp，UDP 丢包会让画面撕裂
- 读不到帧就返回 None，由 runner 决定是否重连
"""

from __future__ import annotations

import subprocess

from PIL import Image

from .base import FrameSource


class RtspSource(FrameSource):
    kind = "rtsp"

    def __init__(self, spec, **opts) -> None:
        super().__init__(spec, **opts)
        self.fps = float(opts.get("fps", 3.0))
        self.width = int(opts.get("width", 640))
        self.height = int(opts.get("height", 480))
        self.transport = opts.get("transport", "tcp")
        self._proc = None
        self._frame_bytes = self.width * self.height * 3
        self._last = 0.0

    def _open(self) -> None:
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-rtsp_transport", self.transport,
            "-i", self.spec.target,
            "-an", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-vf", f"fps={self.fps},scale={self.width}:{self.height}",
            "-",
        ]
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=self._frame_bytes * 2)

    def _read(self):
        if self._proc is None or self._proc.stdout is None:
            return None
        buf = self._proc.stdout.read(self._frame_bytes)
        if not buf or len(buf) < self._frame_bytes:
            return None  # 断流：交给 runner 处理
        return Image.frombytes("RGB", (self.width, self.height), buf)

    def _close(self) -> None:
        if self._proc is not None:
            try:
                if self._proc.stdout:
                    self._proc.stdout.close()
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
            self._proc = None

    def stats(self) -> dict:
        s = super().stats()
        s["transport"] = self.transport
        return s
