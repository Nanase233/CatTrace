"""联调层：把摄像头、猫脸、剪耳三个模块串起来，产出对外事件。

外力只需要看两个契约：DetectionEvent（识别结果）和 ActionEvent（要执行的动作）。
"""

from .aggregate import TrackAggregator
from .bus import EventBus
from .decide import DecisionConfig, DecisionEngine
from .store import Store

__all__ = ["EventBus", "TrackAggregator", "DecisionEngine", "DecisionConfig", "Store"]
