"""猫脸模块（猫脸识别）的 Mock —— 摄像头模块写，猫脸模块负责替换成真实现。"""

from __future__ import annotations

import random

from catvision_contracts import CatFace, FramePacket, HeadPose, Identity, Landmarks, Quality

# 假猫档案：真实现接 gallery 之前，用固定几只猫保证决策链路可测
FAKE_CATS = [
    ("cat-001", "大橘", 0.91),
    ("cat-002", "小黑", 0.86),
    ("cat-003", "三花", 0.83),
]


class MockCatFaceModule:
    """实现 CatFaceModule 协议（mocks 里不做静态断言，由 tests 校验）。"""

    def __init__(
        self,
        *,
        seed: int = 7,
        gallery_version: str = "mock-gallery-v1",
        unknown_ratio: float = 0.0,
        multi_cat_ratio: float = 0.0,
        with_ear_tips: bool = True,
    ) -> None:
        self.rng = random.Random(seed)
        self.gallery_version = gallery_version
        self.unknown_ratio = unknown_ratio
        self.multi_cat_ratio = multi_cat_ratio
        self.with_ear_tips = with_ear_tips
        # track_id -> 该 track 的身份。关键：同一只猫的身份必须跨帧稳定，
        # 否则投票聚合永远得不出多数票（真模型靠 reid，Mock 靠这张表）。
        self._identity: dict[str, tuple[str | None, str | None, float, str]] = {}

    def analyze(self, packet: FramePacket) -> list[CatFace]:
        n = 1
        if self.multi_cat_ratio > 0 and self.rng.random() < self.multi_cat_ratio:
            n = 2

        faces: list[CatFace] = []
        for i in range(n):
            track_id = f"t-{i + 1:04d}"  # 同一段视频里 track_id 稳定
            faces.append(self._build_face(packet, track_id, slot=i))
        return faces

    def _identity_of(self, track_id: str) -> tuple[str | None, str | None, float, str]:
        """首次见到这个 track 时抽一次身份，之后一直复用。"""
        if track_id not in self._identity:
            if self.rng.random() < self.unknown_ratio:
                self._identity[track_id] = (None, None, round(self.rng.uniform(0.40, 0.72), 3), "unknown")
            else:
                cat_id, name, base = self.rng.choice(FAKE_CATS)
                sim = round(min(0.99, base + self.rng.uniform(-0.03, 0.06)), 3)
                self._identity[track_id] = (cat_id, name, sim, "matched")
        return self._identity[track_id]

    def reset(self) -> None:
        """同一段视频换一段时清空，模拟「新来的猫」。"""
        self._identity.clear()

    def _build_face(self, packet: FramePacket, track_id: str, *, slot: int = 0) -> CatFace:
        w, h = packet.width, packet.height
        bw = w * 0.34
        bh = h * 0.42
        x = w * (0.30 if slot == 0 else 0.62) - bw / 2
        y = h * 0.28
        bbox = [round(x, 2), round(y, 2), round(bw, 2), round(bh, 2)]

        cat_id, name, sim, decision = self._identity_of(track_id)

        cx = x + bw / 2
        eye_y = y + bh * 0.42
        ear_base_y = y + bh * 0.10

        def pt(px: float, py: float) -> list[float]:
            return [round(px, 2), round(py, 2)]

        land = Landmarks(
            left_eye=pt(cx - bw * 0.18, eye_y),
            right_eye=pt(cx + bw * 0.18, eye_y),
            nose=pt(cx, y + bh * 0.62),
            left_ear_base=pt(cx - bw * 0.28, ear_base_y),
            right_ear_base=pt(cx + bw * 0.28, ear_base_y),
            left_ear_tip=pt(cx - bw * 0.38, y - bh * 0.06) if self.with_ear_tips else None,
            right_ear_tip=pt(cx + bw * 0.38, y - bh * 0.06) if self.with_ear_tips else None,
        )

        return CatFace(
            packet_id=packet.packet_id,
            track_id=track_id,
            bbox=bbox,
            det_score=round(self.rng.uniform(0.80, 0.98), 3),
            landmarks=land,
            head_pose=HeadPose(
                yaw=round(self.rng.uniform(-12, 12), 2),
                pitch=round(self.rng.uniform(-8, 8), 2),
                roll=round(self.rng.uniform(-6, 6), 2),
            ),
            identity=Identity(
                cat_id=cat_id,
                name=name,
                similarity=sim,
                decision=decision,
                gallery_version=self.gallery_version,
            ),
            quality=Quality(
                blur=round(self.rng.uniform(60, 220), 2),
                brightness=round(self.rng.uniform(90, 180), 2),
                is_usable=True,
            ),
        )
