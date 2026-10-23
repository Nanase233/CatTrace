"""模块接口 Protocol —— 猫脸和耳标模块只要实现这两个方法就能接进主流水线。

主流水线（pipeline/runner.py）只依赖这里的协议，不依赖任何具体实现。
所以三个模块可以完全并行开发：谁先做完就换成真实现，没做完的继续用 mocks/。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import CatFace, EarNotch, FramePacket


@runtime_checkable
class CatFaceModule(Protocol):
    """猫脸模块的模块要实现这个接口。"""

    def analyze(self, packet: FramePacket) -> list[CatFace]:
        """输入一帧，输出画面里所有猫的脸部结果。

        要求：
        - bbox 用 [x, y, w, h]（左上角 + 宽高），基于 packet.width/height
        - landmarks 必须输出全部 7 个点（耳尖不可见给 null）
        - track_id 在同一段视频内对同一只猫保持一致
        - 不认识就说 unknown，不要强行匹配最近邻
        """
        ...


@runtime_checkable
class EarNotchModule(Protocol):
    """耳标模块的模块要实现这个接口。"""

    def analyze(self, packet: FramePacket, faces: list[CatFace]) -> list[EarNotch]:
        """输入一帧 + 猫脸模块的脸部结果，输出剪耳/绝育判断。

        要求：
        - 耳部 ROI 从 faces[i].landmarks 裁剪，不要自己检测猫脸
        - 耳朵不可见时 visible=false 且 notched=null（schema 会强制校验）
        - 输出长度应与 faces 一一对应（用 track_id 对齐）
        """
        ...
