"""树莓派 CSI 摄像头源（picamera2）。

硬件：Raspberry Pi 4 + IMX219（官方 Camera Module v2），已实测 3280x2464，1080p@47fps。

为什么用双流（lores + main）：
- lores 640x480：给 AI 推理，小、快
- main 1080p：只在需要出图/存档时用（proto 阶段默认不用，省内存）
1GB 内存的 Pi4 上，单流反而更稳，所以默认只开 lores。

注意：picamera2 是 apt 装的系统包，venv 必须用 --system-site-packages 才看得见。
"""

from __future__ import annotations

from PIL import Image

from .base import FrameSource


class CsiSource(FrameSource):
    kind = "csi"

    def __init__(self, spec, **opts) -> None:
        super().__init__(spec, **opts)
        self.width = int(opts.get("width", 640))
        self.height = int(opts.get("height", 480))
        self.fps = float(opts.get("fps", 3.0))
        self.dual_stream = bool(opts.get("dual_stream", False))
        self.main_size = tuple(opts.get("main_size", (1920, 1080)))
        self.warmup = float(opts.get("warmup", 1.0))
        self._picam = None
        self._camera = None
        self._last = 0.0

    def _open(self) -> None:
        try:
            from picamera2 import Picamera2
        except ImportError as e:
            raise RuntimeError(
                "没找到 picamera2。树莓派上请先：sudo apt install -y python3-picamera2，"
                "并且 venv 必须用 --system-site-packages 创建。"
            ) from e

        idx = int(self.spec.target or 0)
        self._picam = Picamera2(camera_num=idx)
        lores = {"size": (self.width, self.height), "format": "RGB888"}

        if self.dual_stream:
            cfg = self._picam.create_preview_configuration(
                main={"size": self.main_size, "format": "RGB888"},
                lores=lores,
                buffer_count=4,
            )
        else:
            cfg = self._picam.create_video_configuration(
                main=lores,
                buffer_count=4,
                controls={"FrameRate": float(self.fps)},
            )
        self._picam.configure(cfg)
        self._picam.start()
        if self.warmup > 0:
            import time

            time.sleep(self.warmup)  # 曝光/白平衡收敛，否则前几帧全黑

    def _read(self):

        self._last = self._sleep_to_fps(1.0 / self.fps, self._last)
        arr = self._picam.capture_array("lores" if self.dual_stream else "main")
        if arr is None:
            return None
        if arr.ndim == 3 and arr.shape[2] >= 3:
            arr = arr[:, :, :3]
        img = Image.fromarray(arr, "RGB")
        if img.size != (self.width, self.height):
            img = img.resize((self.width, self.height))
        return img

    def _close(self) -> None:
        if self._picam is not None:
            try:
                self._picam.stop()
            except Exception:
                pass
            try:
                self._picam.close()
            except Exception:
                pass
            self._picam = None

    def capture_main(self):
        """需要高清图时单独调（例如出「最佳帧」快照）。"""
        if not self.dual_stream or self._picam is None:
            raise RuntimeError("需要 dual_stream=True 才能取 main 流")
        arr = self._picam.capture_array("main")
        return Image.fromarray(arr[:, :, :3], "RGB")

    def stats(self) -> dict:
        s = super().stats()
        s.update({"dual_stream": self.dual_stream, "camera_index": int(self.spec.target or 0)})
        return s
