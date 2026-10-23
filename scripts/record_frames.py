#!/usr/bin/env python3
"""录制素材：把摄像头画面存成图片序列，给猫脸、耳标模块做训练/测试数据。

    python scripts/record_frames.py --source csi://0 --fps 2 --seconds 300 --out datasets/raw/2026-10-22
    python scripts/record_frames.py --source file:clips/a.mp4 --fps 5 --out datasets/raw/a

产出：
    <out>/frames/*.jpg    原始帧（下游标注用）
    <out>/meta.jsonl      每帧的 FramePacket（保留 seq / 时间戳，方便对齐）

注意：原始视频不进 Git。datasets/ 和 *.mp4 已在 .gitignore 里。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.camera.capture import CameraStream  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--seconds", type=float, default=0, help="录多久（0=按 --frames）")
    ap.add_argument("--frames", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--camera-id", default="cam0")
    ap.add_argument("--keep-frames", type=int, default=0, help="0=不清理，全部都留")
    args = ap.parse_args()

    out = Path(args.out)
    frames_dir = out / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.jsonl"

    limit = args.frames
    if args.seconds > 0:
        limit = int(args.seconds * args.fps) or 1

    t0 = time.monotonic()
    n = 0
    with CameraStream(
        args.source, fps=args.fps, camera_id=args.camera_id,
        frame_root=out, keep_frames=args.keep_frames,
    ) as cam, meta_path.open("w", encoding="utf-8") as meta:
        for packet in cam.packets(max_frames=limit):
            n += 1
            # 录制的帧挪到 frames/ 下，保持目录干净
            src = Path(packet.image_path)
            dst = frames_dir / f"{packet.seq:06d}.jpg"
            src.replace(dst)
            packet.image_path = str(dst)
            meta.write(json.dumps(packet.to_dict(), ensure_ascii=False) + "\n")
            if n % 20 == 0:
                print(f"  {n} 帧  {n / (time.monotonic() - t0):.2f} fps", file=sys.stderr)

    print(f"完成：{n} 帧 -> {frames_dir}")
    print(f"      元数据 -> {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
