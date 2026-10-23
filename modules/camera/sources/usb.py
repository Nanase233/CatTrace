"""USB / UVC 摄像头源（OpenCV V4L2）。

备用方案：IMX219 夜间不可用（带 IR-cut），夜视模组多是 UVC 设备，走这条路。
"""

from __future__ import annotations

from PIL import Image

from .base import FrameSource


class UsbSource(FrameSource):
    kind = "usb"

    def __init__(self, spec, **opts) -> None:
        super().__init__(spec, **opts)
        self.width = int(opts.get("width", 640))
        self.height = int(opts.get("height", 480))
        self.fps = float(opts.get("fps", 3.0))
        self._cap = None
        self._last = 0.0

    def _open(self) -> None:
        try:
            import cv2
        except ImportError as e:
            raise RuntimeError("USB 源需要 opencv：pip install opencv-python-headless") from e

        idx = int(self.spec.target or 0)
        cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
        if not cap.isOpened():
            raise RuntimeError(f"打不开 USB 摄像头 /dev/video{idx}")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(cv2.CAP_PROP_FPS, max(self.fps, 10.0))
        self._cap = cap
        self._cv2 = cv2

    def _read(self):
        self._last = self._sleep_to_fps(1.0 / self.fps, self._last)
        ok, frame = self._cap.read()
        if not ok:
            return None
        frame = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)
        return Image.fromarray(frame)
