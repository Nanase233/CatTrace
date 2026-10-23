"""猫脸模块：猫脸检测 + 个体识别 + 追踪。

这里现在只有一个占位实现，用来证明接口接通了。
真实现由猫脸模块替换，只要满足 CatFaceModule 协议即可：

    from catvision_contracts import CatFace, FramePacket

    class M1CatFaceModule:
        def analyze(self, packet: FramePacket) -> list[CatFace]: ...

替换方式（不用改流水线一行代码）：

    python -m pipeline.runner --source csi://0 \
        --catface modules.catface:M1CatFaceModule --earnotch mocks:MockEarNotchModule
"""

from __future__ import annotations

from catvision_contracts import CatFace, FramePacket


class NotImplementedYet:
    """占位：调用即报错，避免「静默返回空列表」这种更危险的失败方式。"""

    def analyze(self, packet: FramePacket) -> list[CatFace]:
        raise NotImplementedError(
            "猫脸模块还没实现。先用 mocks.MockCatFaceModule 跑通链路，见 modules/catface/README.md"
        )
