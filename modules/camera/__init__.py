"""摄像头模块：摄像头接入模块。

对外只做一件事：把各种视频源统一成 FramePacket 流。

支持源：
    csi://0                  树莓派 CSI 排线摄像头（picamera2）
    usb://0                  USB / UVC 摄像头（OpenCV V4L2）
    rtsp://user:pass@ip/...  RTSP 网络摄像头（ffmpeg 拉流）
    file:/path/to/dir        图片目录回放
    file:/path/to.mp4        视频文件回放
    synthetic:60             合成源（无硬件也能跑，联调用）
"""

from .frame_writer import FrameWriter
from .source import SourceSpec, open_source, parse_source
from .ticker import FrameRateMeter, Ticker

__all__ = ["FrameWriter", "FrameRateMeter", "Ticker", "SourceSpec", "open_source", "parse_source"]
