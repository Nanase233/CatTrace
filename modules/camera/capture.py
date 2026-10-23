"""把 FrameSource 变成一个 FramePacket 生成器。

这是摄像头模块对外的唯一出口：下游（pipeline / 猫脸 / 耳标模块）只认 FramePacket。
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field

from catvision_contracts import FramePacket

from .frame_writer import FrameWriter
from .source import SourceSpec, open_source
from .ticker import FrameRateMeter, Ticker

log = logging.getLogger("catvision.camera")


@dataclass
class CaptureStats:
    captured: int = 0
    dropped: int = 0
    emitted: int = 0
    first_at: float = 0.0
    last_at: float = 0.0
    extra: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        span = self.last_at - self.first_at if self.last_at > self.first_at else 0.0
        d = {
            "captured": self.captured,
            "dropped": self.dropped,
            "emitted": self.emitted,
            "elapsed_s": round(span, 3),
            "effective_fps": round(self.emitted / span, 2) if span > 0 else 0.0,
        }
        d.update(self.extra)
        return d


class CameraStream:
    """CSI / USB / RTSP / 文件 / 合成 的统一入口。

    用法：
        with CameraStream("csi://0", fps=3) as cam:
            for packet in cam.packets(max_frames=10):
                ...
    """

    def __init__(
        self,
        source: str | SourceSpec,
        *,
        fps: float = 3.0,
        camera_id: str = "cam0",
        frame_root: str | None = None,
        keep_frames: int = 120,
        fmt: str = "jpeg",
        width: int | None = None,
        height: int | None = None,
        loop: bool = False,
        max_consecutive_failures: int = 30,
    ) -> None:
        self.spec = source if isinstance(source, SourceSpec) else None
        opts = {"fps": fps, "loop": loop}
        if width:
            opts["width"] = width
        if height:
            opts["height"] = height
        self.source = open_source(source, **opts)
        self.camera_id = camera_id
        self.fps = float(fps)
        self.ticker = Ticker(self.fps)
        self.meter = FrameRateMeter()
        self.writer = FrameWriter(frame_root, camera_id=camera_id, fmt=fmt, keep=keep_frames)
        self.stats = CaptureStats()
        self.max_consecutive_failures = max_consecutive_failures
        self._seq = 0
        self._opened = False

    # -- 生命周期 ---------------------------------------------------------
    def open(self) -> CameraStream:
        self.source.open()
        self._opened = True
        log.info("摄像头已打开：%s  %dx%d", self.source.uri, self.source.width, self.source.height)
        return self

    def close(self) -> None:
        if self._opened:
            self.source.close()
            self._opened = False

    def __enter__(self) -> CameraStream:
        return self.open()

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- 主入口 -----------------------------------------------------------
    def packets(self, max_frames: int = 0) -> Iterator[FramePacket]:
        """max_frames=0 表示一直读直到源结束。"""
        import time

        consecutive = 0
        while max_frames <= 0 or self.stats.emitted < max_frames:
            self.ticker.wait()
            img = self.source.read()

            if img is None:
                consecutive += 1
                self.stats.dropped += 1
                if consecutive >= self.max_consecutive_failures:
                    log.warning("连续 %d 次读帧失败，停止采集", consecutive)
                    return
                if not self._may_retry():
                    return
                continue

            consecutive = 0
            now = time.monotonic()
            if self.stats.first_at == 0.0:
                self.stats.first_at = now
            self.stats.last_at = now
            self.stats.captured += 1

            packet = self._to_packet(img)
            self.meter.tick()
            self.stats.emitted += 1
            yield packet

    def _may_retry(self) -> bool:
        """源读不出帧时，能不能继续（文件源读完就结束，摄像头源可以重试）。"""
        return self.source.kind in ("csi", "usb", "rtsp")

    def _to_packet(self, img) -> FramePacket:
        seq = self._seq
        self._seq += 1
        path, sha1 = self.writer.write(img, seq=seq)
        return FramePacket.build(
            camera_id=self.camera_id,
            seq=seq,
            width=img.size[0],
            height=img.size[1],
            image_path=str(path),
            source=self.source.source_info(),
            fmt=self.writer.fmt,
            image_sha1=sha1,
        )

    def stats_dict(self) -> dict:
        d = self.stats.as_dict()
        d["measured_fps"] = round(self.meter.fps, 2)
        d["source"] = self.source.stats()
        d["frames_dir"] = self.writer.stats()
        return d
