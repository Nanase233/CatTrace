"""CLI：单独跑摄像头模块，验证采集链路。

    python -m modules.camera --source synthetic:5
    python -m modules.camera --source csi://0 --fps 3 --frames 10
    python -m modules.camera --source file:./clips/sample.mp4 --loop
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

from .capture import CameraStream


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m modules.camera", description="CatVision 摄像头模块")
    p.add_argument("--source", required=True, help="csi://0 | usb://0 | rtsp://... | file:/path | synthetic:N")
    p.add_argument("--fps", type=float, default=3.0, help="抽帧帧率（默认 3）")
    p.add_argument("--frames", type=int, default=0, help="取多少帧后停（0=不限）")
    p.add_argument("--camera-id", default="cam0")
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.add_argument("--loop", action="store_true", help="文件源循环播放")
    p.add_argument("--keep-frames", type=int, default=120, help="帧目录保留最近多少帧")
    p.add_argument("--frame-root", default=None, help="帧落盘目录（默认 /dev/shm/catvision/frames）")
    p.add_argument("--stats-every", type=int, default=0, help="每 N 帧打印一次状态")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    t0 = time.monotonic()
    n = 0
    try:
        with CameraStream(
            args.source,
            fps=args.fps,
            camera_id=args.camera_id,
            frame_root=args.frame_root,
            keep_frames=args.keep_frames,
            width=args.width,
            height=args.height,
            loop=args.loop,
        ) as cam:
            for packet in cam.packets(max_frames=args.frames):
                n += 1
                print(json.dumps(packet.to_dict(), ensure_ascii=False))
                if args.stats_every and n % args.stats_every == 0:
                    print("  -- " + json.dumps(cam.stats_dict(), ensure_ascii=False), file=sys.stderr)
            print("-- " + json.dumps(cam.stats_dict(), ensure_ascii=False), file=sys.stderr)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"摄像头模块失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - t0
    print(f"CAMERA OK  frames={n}  elapsed={elapsed:.2f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
