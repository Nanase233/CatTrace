"""帧落盘。

Pi4 上 1GB 内存、SD 卡寿命有限，所以：
- 默认写 /dev/shm（tmpfs，内存盘，重启即清），绝不写 SD 卡
- 只保留最近 N 帧，自动清理旧帧（环形缓冲）
- 只暴露路径给下游，不通过内存传图（多进程/跨语言都能用）
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

DEFAULT_QUALITY = 88
DEFAULT_KEEP = 120


def default_frame_root() -> Path:
    """优选 /dev/shm（Linux tmpfs）；Windows / 无 dev tmpfs 时退回临时目录。"""
    shm = Path("/dev/shm")
    if shm.is_dir() and os.access(shm, os.W_OK):
        return shm / "catvision" / "frames"
    return Path(tempfile.gettempdir()) / "catvision" / "frames"


class FrameWriter:
    """把一帧图像写进帧目录，返回 (路径, sha1)。"""

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        camera_id: str = "cam0",
        fmt: str = "jpeg",
        quality: int = DEFAULT_QUALITY,
        keep: int = DEFAULT_KEEP,
    ) -> None:
        if fmt not in ("jpeg", "png"):
            raise ValueError(f"format 只能是 jpeg/png，收到 {fmt!r}")
        self.root = Path(root) if root else default_frame_root()
        self.camera_id = camera_id
        self.fmt = fmt
        self.quality = quality
        self.keep = keep
        self.dir = self.root / camera_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self._written: list[Path] = []

    @property
    def extension(self) -> str:
        return "jpg" if self.fmt == "jpeg" else "png"

    def write(self, image, *, seq: int) -> tuple[Path, str]:
        """image 可以是 PIL.Image 或任何有 .save(fp, format=...) 的对象。"""
        path = self.dir / f"f{seq:06d}.{self.extension}"
        fmt = "JPEG" if self.fmt == "jpeg" else "PNG"
        kwargs = {"quality": self.quality} if self.fmt == "jpeg" else {}
        rgb = image.convert("RGB") if hasattr(image, "convert") else image
        rgb.save(path, format=fmt, **kwargs)

        sha1 = hashlib.sha1(path.read_bytes()).hexdigest()
        self._written.append(path)
        self._prune()
        return path, sha1

    def _prune(self) -> None:
        if self.keep <= 0:
            return
        while len(self._written) > self.keep:
            old = self._written.pop(0)
            try:
                old.unlink()
            except FileNotFoundError:
                pass

    def clear(self) -> None:
        """清空本机摄像头帧目录（重启流水线 / 换源时用）。"""
        if self.dir.is_dir():
            shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._written.clear()

    def stats(self) -> dict:
        files = sorted(self.dir.glob(f"*.{self.extension}"))
        total = sum(f.stat().st_size for f in files)
        return {
            "dir": str(self.dir),
            "files": len(files),
            "bytes": total,
            "mb": round(total / 1024 / 1024, 3),
        }
