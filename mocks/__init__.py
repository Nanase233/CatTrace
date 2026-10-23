"""三个模块各自模块的 Mock 实现。

没有 Mock 就没有并行开发：任何人没做完，其他人的流水线也必须能跑通。
每个 Mock 的调用签名必须和真实现严格一致。

| Mock | 替代谁 | 产出 |
|---|---|---|
| MockCatFaceModule | 猫脸模块 | CatFace[] |
| MockEarNotchModule | 耳标模块 | EarNotch[] |
| MockCameraSource | 摄像头模块（摄像头） | FramePacket |
"""

from .mock_camera import MockCameraSource, make_packet
from .mock_catface import MockCatFaceModule
from .mock_earnotch import MockEarNotchModule

__all__ = ["MockCameraSource", "make_packet", "MockCatFaceModule", "MockEarNotchModule"]
