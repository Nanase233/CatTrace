"""耳标模块：剪耳 / 绝育耳标识别 + 绝育状态绑定。

真实现要满足 EarNotchModule 协议：

    from catvision_contracts import CatFace, EarNotch, FramePacket

    class EarNotchModel:
        def analyze(self, packet: FramePacket, faces: list[CatFace]) -> list[EarNotch]: ...

替换方式：

    python -m pipeline.runner --source csi://0 \
        --catface mocks:MockCatFaceModule --earnotch modules.earnotch:EarNotchModel
"""

from __future__ import annotations

from catvision_contracts import CatFace, EarNotch, FramePacket


class NotImplementedYet:
    def analyze(self, packet: FramePacket, faces: list[CatFace]) -> list[EarNotch]:
        raise NotImplementedError(
            "剪耳模块还没实现。先用 mocks.MockEarNotchModule 跑通链路，见 modules/earnotch/README.md"
        )
