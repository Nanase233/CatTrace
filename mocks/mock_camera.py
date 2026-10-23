"""摄像头的 Mock —— 不接任何硬件也能造出合法的 FramePacket。"""

from __future__ import annotations

import hashlib
from pathlib import Path

from catvision_contracts import FramePacket, SourceInfo


def make_packet(
    *,
    seq: int = 0,
    camera_id: str = "cam-mock",
    width: int = 640,
    height: int = 480,
    image_path: str | Path = "/dev/shm/catvision/frames/mock.jpg",
    fmt: str = "jpeg",
) -> FramePacket:
    """造一个字段全合法的 FramePacket（文件不存在也允许，纯元数据场景用）。"""
    return FramePacket.build(
        camera_id=camera_id,
        seq=seq,
        width=width,
        height=height,
        image_path=str(image_path),
        source=SourceInfo(kind="synthetic", uri="synthetic:mock"),
        fmt=fmt,
    )


class MockCameraSource:
    """最简单的合成源：真的画图 + 真的落盘，只是画面是程序生成的。

    这样下游（猫脸、耳标模块）拿到的东西和真摄像头完全一样。
    """

    def __init__(self, *, width: int = 640, height: int = 480, camera_id: str = "cam-mock") -> None:
        self.width = width
        self.height = height
        self.camera_id = camera_id
        self.uri = "synthetic:mock"

    def read(self, seq: int = 0) -> tuple[bytes, str]:
        """返回 (jpeg 字节, sha1)。"""
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (self.width, self.height), (70, 74, 82))
        d = ImageDraw.Draw(img)
        d.ellipse([self.width * 0.3, self.height * 0.25, self.width * 0.7, self.height * 0.75], fill=(196, 150, 96))
        buf = __import__("io").BytesIO()
        img.save(buf, format="JPEG", quality=88)
        data = buf.getvalue()
        return data, hashlib.sha1(data).hexdigest()
