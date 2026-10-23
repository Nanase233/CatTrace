"""具体源实现。每个源只负责「给我一帧 PIL.Image」，别的什么都不做。"""

from .base import FrameSource

__all__ = ["FrameSource"]
