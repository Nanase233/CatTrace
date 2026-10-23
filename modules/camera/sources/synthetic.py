"""合成源：程序画一只「猫」，不需要任何硬件。

用途：
- D0 验收（CI / Windows / 没摄像头时）
- 猫脸、耳标模块在自己电脑上开发时当输入
- 压测：synthetic:600 跑 600 帧看管线稳不稳
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

from .base import FrameSource

CAT_FUR = ((196, 150, 96), (60, 62, 68), (222, 214, 200), (150, 110, 70))


class SyntheticSource(FrameSource):
    kind = "synthetic"

    def __init__(self, spec, **opts) -> None:
        super().__init__(spec, **opts)
        self.n_frames = self._parse_count(spec.target)
        self.fps = float(opts.get("fps", 3.0))
        self.seed = int(opts.get("seed", 20261022))
        self.rng = random.Random(self.seed)
        self.width = int(opts.get("width", 640))
        self.height = int(opts.get("height", 480))
        self._i = 0

    @staticmethod
    def _parse_count(target: str) -> int:
        target = (target or "").strip()
        if not target or target in ("infinite", "inf", "0"):
            return 0  # 0 = 不限
        try:
            return int(target)
        except ValueError as e:
            raise ValueError(f"synthetic: 后面要跟帧数，例如 synthetic:60（收到 {target!r}）") from e

    def _open(self) -> None:
        pass

    def _read(self):
        if self.n_frames and self._i >= self.n_frames:
            self.at_eof = True
            return None
        img = self._render(self._i)
        self._i += 1
        return img

    def _render(self, i: int) -> Image.Image:
        w, h = self.width, self.height
        img = Image.new("RGB", (w, h), (58, 62, 70))
        d = ImageDraw.Draw(img)

        # 地面 / 背景渐变，让清晰度指标有变化
        d.rectangle([0, int(h * 0.62), w, h], fill=(46, 50, 58))
        # 轻微漂移，模拟猫在动
        dx = math.sin(i / 7.0) * w * 0.06
        dy = math.cos(i / 11.0) * h * 0.02

        fur = CAT_FUR[i // 12 % len(CAT_FUR)]
        cx, cy = w * 0.5 + dx, h * 0.55 + dy
        fw, fh = w * 0.34, h * 0.46

        # 耳朵（两个三角）
        for sign in (-1, 1):
            ex = cx + sign * fw * 0.30
            d.polygon(
                [(ex - fw * 0.16, cy - fh * 0.34), (ex + fw * 0.16, cy - fh * 0.34), (ex, cy - fh * 0.62)],
                fill=fur,
            )
        # 头
        d.ellipse([cx - fw / 2, cy - fh / 2, cx + fw / 2, cy + fh / 2], fill=fur)
        # 眼睛
        for sign in (-1, 1):
            ex = cx + sign * fw * 0.19
            d.ellipse([ex - fw * 0.055, cy - fh * 0.10, ex + fw * 0.055, cy + fh * 0.02], fill=(30, 32, 36))
        # 鼻子
        d.polygon(
            [(cx - fw * 0.05, cy + fh * 0.12), (cx + fw * 0.05, cy + fh * 0.12), (cx, cy + fh * 0.20)],
            fill=(214, 132, 140),
        )
        # 胡须
        for sign in (-1, 1):
            for k in range(3):
                y0 = cy + fh * (0.14 + k * 0.045)
                d.line(
                    [(cx + sign * fw * 0.10, y0), (cx + sign * fw * 0.55, y0 - fh * 0.03 + k * fh * 0.03)],
                    fill=(232, 232, 228),
                    width=1,
                )

        # 每 10 帧加一次运动模糊，制造「质量不佳」样本给上游练手
        if i % 10 == 7:
            img = img.filter(ImageFilter.GaussianBlur(2.2))
        return img

    def stats(self) -> dict:
        s = super().stats()
        s["n_frames"] = self.n_frames
        return s
