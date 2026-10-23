"""文件回放源。

两种模式：
- 目录（图片集）：按文件名排序逐张读，loop 可循环
- 视频文件（mp4/mkv/mov/avi）：走 ffmpeg 抽帧管道

为什么重要：猫脸、耳标模块没有摄像头，也能用录好的素材跑完整链路。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image

from .base import FrameSource

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".avi", ".m4v", ".ts"}


class FileSource(FrameSource):
    kind = "file"

    def __init__(self, spec, **opts) -> None:
        super().__init__(spec, **opts)
        self.loop = bool(opts.get("loop", False))
        self.fps = float(opts.get("fps", 3.0))
        self.path = self._resolve(spec.target)
        self._images: list[Path] = []
        self._idx = 0
        self._proc: subprocess.Popen | None = None
        self._last_read = 0.0
        self._frame_bytes = None
        self._video_mode = False

    @staticmethod
    def _resolve(target: str) -> Path:
        p = Path(target)
        if not p.exists():
            raise FileNotFoundError(f"源路径不存在：{p}")
        return p

    def _open(self) -> None:
        if self.path.is_dir():
            self._images = sorted(
                f for f in self.path.iterdir() if f.suffix.lower() in IMAGE_EXT
            )
            if not self._images:
                raise FileNotFoundError(f"目录里没有图片：{self.path}")
            with Image.open(self._images[0]) as im:
                self.width, self.height = im.size
            return

        if self.path.suffix.lower() in VIDEO_EXT:
            self._open_video()
            return

        if self.path.suffix.lower() in IMAGE_EXT:
            self._images = [self.path]
            with Image.open(self.path) as im:
                self.width, self.height = im.size
            return

        raise ValueError(f"不认识的文件类型：{self.path.suffix}")

    def _open_video(self) -> None:
        """用 ffmpeg 输出固定尺寸的原始 RGB 帧流，自己按 fps 抽帧。"""
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "csv=p=0", str(self.path),
            ],
            capture_output=True, text=True, check=True,
        )
        w, h = (int(x) for x in probe.stdout.strip().split(",")[:2])
        self.width, self.height = w, h
        self._video_mode = True
        self._frame_bytes = w * h * 3
        self._last_read = 0.0
        # -re 按实时速度喂帧，保证和真摄像头节奏一致
        self._proc = subprocess.Popen(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-re",
                "-i", str(self.path),
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
            ],
            stdout=subprocess.PIPE,
            bufsize=self._frame_bytes * 2,
        )

    def _read(self):
        if self._video_mode:
            return self._read_video()
        return self._read_image()

    def _read_image(self):
        if self._idx >= len(self._images):
            if not self.loop:
                self.at_eof = True
                return None
            self._idx = 0
        path = self._images[self._idx]
        self._idx += 1
        return Image.open(path).convert("RGB")

    def _read_video(self):
        self._last_read = self._sleep_to_fps(1.0 / self.fps, self._last_read)
        assert self._proc and self._proc.stdout
        buf = self._proc.stdout.read(self._frame_bytes)
        if not buf or len(buf) < self._frame_bytes:
            if self.loop:
                self.close()
                self._open()
                return self._read_video()
            self.at_eof = True
            return None
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
        s.update({"path": str(self.path), "mode": "video" if self._video_mode else "image"})
        return s
