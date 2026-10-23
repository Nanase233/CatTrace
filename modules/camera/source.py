"""视频源统一抽象：字符串 URI -> 具体 FrameSource。

对下游来说，无论帧来自 CSI 摄像头还是合成器，都是同样的 FramePacket。
这条「源等价」保证是猫脸、耳标模块能并行开发的前提。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from catvision_contracts import SourceInfo

KINDS = ("csi", "usb", "rtsp", "file", "synthetic")


@dataclass(frozen=True)
class SourceSpec:
    kind: str
    uri: str
    target: str

    def to_source_info(self) -> SourceInfo:
        return SourceInfo(kind=self.kind, uri=self.uri)

    def __str__(self) -> str:
        return f"{self.kind}:{self.target}"


def parse_source(raw: str) -> SourceSpec:
    """解析源字符串。

    csi://0 | usb://0 | rtsp://... | file:path | file:///abs/path | synthetic:60
    裸路径（/data/frames、D:\\frames、sample.mp4）按 file: 处理。
    """
    s = raw.strip()
    if not s:
        raise ValueError("source 不能为空")

    if "://" in s:
        scheme, rest = s.split("://", 1)
        scheme = scheme.lower()
        if scheme == "file":
            return SourceSpec("file", s, rest)
        if scheme in KINDS:
            return SourceSpec(scheme, s, rest)
        raise ValueError(f"不支持的源协议 {scheme!r}，可选 {KINDS}")

    if ":" in s:
        scheme, rest = s.split(":", 1)
        scheme = scheme.lower()
        if scheme in KINDS:
            return SourceSpec(scheme, s, rest)
        # Windows 盘符 D:\x 会走到这里：当成 file
        if len(scheme) == 1:
            return SourceSpec("file", f"file:{s}", s)

    return SourceSpec("file", f"file:{s}", s)


def _spec_of(spec: SourceSpec) -> SourceSpec:
    """rtsp:// 带认证的 URI，拆出 target 给 ffmpeg。"""
    return spec


def open_source(raw: str | SourceSpec, **opts: Any):
    """工厂：按 kind 实例化具体源。返回未 open 的 FrameSource。"""
    spec = raw if isinstance(raw, SourceSpec) else parse_source(raw)
    spec = _spec_of(spec)

    if spec.kind == "synthetic":
        from .sources.synthetic import SyntheticSource

        return SyntheticSource(spec, **opts)
    if spec.kind == "file":
        from .sources.file import FileSource

        return FileSource(spec, **opts)
    if spec.kind == "csi":
        from .sources.csi import CsiSource

        return CsiSource(spec, **opts)
    if spec.kind == "rtsp":
        from .sources.rtsp import RtspSource

        return RtspSource(spec, **opts)
    if spec.kind == "usb":
        from .sources.usb import UsbSource

        return UsbSource(spec, **opts)
    raise ValueError(f"未知源类型 {spec.kind!r}")
