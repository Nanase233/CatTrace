"""摄像头模块单测：源解析、合成源、落盘、节拍。"""

from __future__ import annotations

import pytest
from catvision_contracts import validate

from modules.camera.capture import CameraStream
from modules.camera.frame_writer import FrameWriter, default_frame_root
from modules.camera.source import parse_source
from modules.camera.ticker import FrameRateMeter, Ticker


@pytest.mark.parametrize(
    "raw,kind",
    [
        ("csi://0", "csi"),
        ("usb://0", "usb"),
        ("rtsp://user:pw@10.0.0.9/s1", "rtsp"),
        ("file:/data/frames", "file"),
        ("file:///data/frames", "file"),
        ("synthetic:60", "synthetic"),
        ("/data/frames", "file"),
        ("sample.mp4", "file"),
        ("D:\\clips\\a.mp4", "file"),
    ],
)
def test_parse_source(raw: str, kind: str) -> None:
    assert parse_source(raw).kind == kind


def test_parse_source_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        parse_source("")
    with pytest.raises(ValueError):
        parse_source("ftp://nope/x")


def test_synthetic_source_emits_valid_packets(tmp_path) -> None:
    with CameraStream("synthetic:3", fps=1000, camera_id="camT", frame_root=tmp_path) as cam:
        packets = list(cam.packets(max_frames=3))
    assert len(packets) == 3
    for i, p in enumerate(packets):
        assert p.seq == i
        assert p.camera_id == "camT"
        assert p.format == "jpeg"
        assert p.source.kind == "synthetic"
        validate("frame_packet", p)
        from pathlib import Path

        assert Path(p.image_path).exists(), "帧必须真的落盘（下游靠路径读图）"


def test_frame_writer_prunes(tmp_path) -> None:
    from PIL import Image

    w = FrameWriter(tmp_path, camera_id="c", keep=3)
    img = Image.new("RGB", (32, 32), (10, 20, 30))
    for i in range(6):
        w.write(img, seq=i)
    files = list(w.dir.glob("*.jpg"))
    assert len(files) == 3, f"应只保留最近 3 帧，实际 {len(files)}"
    assert {f.name for f in files} == {"f000003.jpg", "f000004.jpg", "f000005.jpg"}


def test_frame_writer_rejects_bad_format(tmp_path) -> None:
    with pytest.raises(ValueError):
        FrameWriter(tmp_path, fmt="bmp")


def test_default_frame_root_prefers_shm() -> None:
    root = str(default_frame_root())
    assert "frames" in root


def test_file_source_directory(tmp_path) -> None:
    from PIL import Image

    for i in range(4):
        Image.new("RGB", (64, 48), (i * 20, 40, 60)).save(tmp_path / f"img{i:02d}.jpg")
    with CameraStream(f"file:{tmp_path}", fps=1000, camera_id="camF", frame_root=tmp_path / "out") as cam:
        packets = list(cam.packets(max_frames=4))
    assert [p.seq for p in packets] == [0, 1, 2, 3]
    assert packets[0].source.kind == "file"


def test_file_source_ends_without_loop(tmp_path) -> None:
    from PIL import Image

    Image.new("RGB", (64, 48)).save(tmp_path / "only.jpg")
    with CameraStream(f"file:{tmp_path}", fps=1000, camera_id="camF", frame_root=tmp_path / "out") as cam:
        packets = list(cam.packets())
    assert len(packets) == 1, "不 loop 时读完就停，不能死循环"


def test_missing_file_source_raises() -> None:
    with pytest.raises(FileNotFoundError):
        CameraStream("file:/definitely/not/here", fps=3)


def test_ticker_paces() -> None:
    import time

    t = Ticker(20.0)
    t0 = time.monotonic()
    for _ in range(5):
        t.wait()
    elapsed = time.monotonic() - t0
    assert 0.15 < elapsed < 0.60, f"5 帧 @20fps 应该约 0.25s，实际 {elapsed:.3f}s"


def test_ticker_rejects_zero_fps() -> None:
    with pytest.raises(ValueError):
        Ticker(0)


def test_meter() -> None:
    import time

    m = FrameRateMeter()
    for _ in range(5):
        m.tick()
        time.sleep(0.01)
    assert m.fps > 0
    assert m.count == 5
