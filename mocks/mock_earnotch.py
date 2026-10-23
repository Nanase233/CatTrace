"""耳标识别的 Mock —— 摄像头模块写，耳标模块负责替换成真实现。"""

from __future__ import annotations

import random

from catvision_contracts import CatFace, EarNotch, EarSide, FramePacket


class MockEarNotchModule:
    """实现 EarNotchModule 协议。

    默认输出「左耳剪、右耳不剪」（TNR 常见标记），可通过参数改。
    """

    def __init__(
        self,
        *,
        seed: int = 11,
        notched_left: bool = True,
        notched_right: bool = False,
        visible_prob: float = 1.0,
        rule: str = "any_ear_notched",
        model_version: str = "mock-earnotch-v1",
    ) -> None:
        self.rng = random.Random(seed)
        self.notched_left = notched_left
        self.notched_right = notched_right
        self.visible_prob = visible_prob
        self.rule = rule
        self.model_version = model_version

    def analyze(self, packet: FramePacket, faces: list[CatFace]) -> list[EarNotch]:
        return [self._one(packet, f) for f in faces]

    def _one(self, packet: FramePacket, face: CatFace) -> EarNotch:
        left = self._side(face, "left", self.notched_left)
        right = self._side(face, "right", self.notched_right)
        return EarNotch.from_ears(
            packet_id=packet.packet_id,
            track_id=face.track_id,
            left=left,
            right=right,
            rule=self.rule,
            model_version=self.model_version,
        )

    def _side(self, face: CatFace, which: str, notched: bool) -> EarSide:
        visible = self.rng.random() < self.visible_prob
        base = face.landmarks.left_ear_base if which == "left" else face.landmarks.right_ear_base
        tip = face.landmarks.left_ear_tip if which == "left" else face.landmarks.right_ear_tip

        if not visible:
            # 契约硬规则：看不见就说看不见
            return EarSide(visible=False, notched=None, score=None, bbox=None)

        x = min(base[0], tip[0] if tip else base[0])
        y = min(base[1], tip[1] if tip else base[1])
        w = abs((tip[0] if tip else base[0] + 40) - base[0]) + 20
        h = abs(base[1] - (tip[1] if tip else base[1] - 40)) + 20
        return EarSide(
            visible=True,
            notched=notched,
            score=round(self.rng.uniform(0.82, 0.97), 3),
            bbox=[round(x, 2), round(y, 2), round(w, 2), round(h, 2)],
        )
