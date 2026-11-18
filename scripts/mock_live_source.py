#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地假摄像头：模拟树莓派的 MJPEG 推流 + /stats 识别状态，用来联调网页直播。

没有树莓派也能验证「Flask 代理 → 网页直播间」这条链路到底通不通：

    # 1) 起一个假摄像头（默认 8100）
    python scripts/mock_live_source.py --port 8100 --verdict cat

    # 2) 另开一个终端，带地址起网页
    $env:CATTRACE_LIVE_URL      = "http://127.0.0.1:8100/stream"
    $env:CATTRACE_LIVE_STATS    = "http://127.0.0.1:8100/stats"
    $env:CATTRACE_LIVE_SNAPSHOT = "http://127.0.0.1:8100/snapshot.jpg"
    python app.py

    # 3) 打开 http://127.0.0.1:5000/live ，画面应切成「实时」而不是占位表情

提供的端点与 scripts/pi_phone_demo.py 保持一致：

    /            说明页
    /stream      multipart/x-mixed-replace MJPEG（网页直播间用这一路）
    /snapshot.jpg /frame.jpg  单帧 JPEG
    /stats       识别状态 JSON（label / p_cat / verdict / p_notch / stream_frames …）

画面是 Pillow 现画的：渐变背景 + 来回走动的猫形 + 时间戳，不需要摄像头和 opencv。
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO

from PIL import Image, ImageDraw

BOUNDARY = "frame"


class MockState:
    """与树莓派 STATE 对齐的共享状态，供 /stats 读取。"""

    def __init__(self, verdict: str) -> None:
        self.lock = threading.Lock()
        self.verdict = verdict
        # 与树莓派一致：label 是二分类结果（cat / notcat），verdict 是最终判定（cat / nocat）
        self.label = "starting" if verdict == "starting" else ("cat" if verdict == "cat" else "notcat")
        self.p_cat = {"cat": 0.972, "notcat": 0.081, "starting": 0.0}[verdict]
        self.p_notch = 0.63 if verdict == "cat" else None
        self.notched = True if verdict == "cat" else None
        self.frames = 0
        self.stream_frames = 0
        self.stream_fps = 0.0
        self.last_frame_ts = 0.0
        self.started = time.time()
        self.latest_stream_jpg = b""

    def snapshot(self, jpg: bytes) -> None:
        with self.lock:
            now = time.time()
            if self.last_frame_ts:
                dt = now - self.last_frame_ts
                instant = 1.0 / dt if dt > 0 else 0.0
                # EMA 平滑，和树莓派那边的 stream_fps 行为一致
                self.stream_fps = instant if not self.stream_fps else self.stream_fps * 0.8 + instant * 0.2
            self.last_frame_ts = now
            self.latest_stream_jpg = jpg
            self.stream_frames += 1
            self.frames = self.stream_frames

    def stats(self) -> dict:
        with self.lock:
            # 超过 2 秒没新帧就当作 0 fps，避免断开后还挂着一个旧帧率
            fps = self.stream_fps if (self.last_frame_ts and time.time() - self.last_frame_ts < 2) else 0.0
            return {
                "label": self.label,
                "p_cat": round(self.p_cat, 4),
                "fps": 2.0,
                "frames": self.stream_frames,
                "luma": 112.5,
                "stream_fps": round(fps, 2),
                "stream_frames": self.stream_frames,
                "verdict": "cat" if self.verdict == "cat" else ("starting" if self.verdict == "starting" else "nocat"),
                "p_notch": self.p_notch,
                "notched": self.notched,
                "ear_enabled": self.verdict == "cat",
                "history": [],
                "mock": True,
            }


def build_frame(size: tuple[int, int], phase: float, verdict: str) -> bytes:
    """画一帧：暖色渐变 + 走动的猫形 + 时间戳/判定文字。"""
    width, height = size
    img = Image.new("RGB", (width, height), (250, 244, 238))
    draw = ImageDraw.Draw(img)

    # 背景竖向渐变，模拟猫屋的木纹暖色
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line(
            [(0, y), (width, y)],
            fill=(int(250 - 26 * t), int(244 - 40 * t), int(238 - 46 * t)),
        )

    # 地板
    draw.rectangle([(0, int(height * 0.74)), (width, height)], fill=(226, 208, 190))

    # 一只来回走动的猫：身体 + 头 + 耳朵 + 尾巴
    cx = width * (0.5 + 0.28 * __import__("math").sin(phase))
    floor = int(height * 0.74)
    body_w, body_h = int(width * 0.18), int(height * 0.20)
    draw.ellipse(
        [(cx - body_w / 2, floor - body_h), (cx + body_w / 2, floor)],
        fill=(228, 150, 60),
    )
    head_r = body_w * 0.42
    head_cx, head_cy = cx + body_w * 0.42, floor - body_h * 0.92
    draw.ellipse(
        [(head_cx - head_r, head_cy - head_r), (head_cx + head_r, head_cy + head_r)],
        fill=(240, 172, 88),
    )
    for dx in (-0.55, 0.45):
        draw.polygon(
            [
                (head_cx + dx * head_r, head_cy - head_r * 0.85),
                (head_cx + (dx + 0.35) * head_r, head_cy - head_r * 1.45),
                (head_cx + (dx + 0.55) * head_r, head_cy - head_r * 0.75),
            ],
            fill=(240, 172, 88),
        )
    # 眼睛 + 鼻子
    for ex in (-0.35, 0.35):
        draw.ellipse(
            [
                (head_cx + ex * head_r - 3, head_cy - 5),
                (head_cx + ex * head_r + 3, head_cy + 1),
            ],
            fill=(60, 48, 44),
        )
    draw.ellipse([(head_cx - 4, head_cy + 6), (head_cx + 4, head_cy + 12)], fill=(196, 120, 120))
    # 尾巴
    draw.arc(
        [
            (cx - body_w * 1.05, floor - body_h * 1.15),
            (cx - body_w * 0.35, floor - body_h * 0.05),
        ],
        start=250,
        end=70,
        fill=(228, 150, 60),
        width=max(4, int(width * 0.012)),
    )

    # 左上角标注，方便确认「看到的是哪一路流」
    stamp = datetime.now().strftime("%H:%M:%S")
    label = {"cat": "MOCK CAM - cat 0.97", "notcat": "MOCK CAM - no cat", "starting": "MOCK CAM - starting"}[verdict]
    draw.rectangle([(0, 0), (width, 34)], fill=(40, 32, 34))
    draw.text((10, 10), "%s | %s" % (label, stamp), fill=(246, 238, 234))

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=78)
    return buf.getvalue()


def make_handler(state: MockState, size: tuple[int, int], fps: float):
    interval = 1.0 / fps if fps > 0 else 0.125

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # 少刷屏
            pass

        def do_GET(self):  # noqa: N802
            path = self.path.split("?")[0]
            if path == "/":
                body = (
                    "<h2>CatTrace 假摄像头</h2>"
                    "<p>端点：/stream、/snapshot.jpg、/frame.jpg、/stats</p>"
                    "<p>当前判定：<b>%s</b></p>" % state.verdict
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/stats":
                body = json.dumps(state.stats(), ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path in ("/snapshot.jpg", "/frame.jpg"):
                jpg = state.latest_stream_jpg or build_frame(size, time.time(), state.verdict)
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(jpg)))
                self.end_headers()
                self.wfile.write(jpg)
                return
            if path == "/stream":
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=%s" % BOUNDARY)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                phase = 0.0
                try:
                    while True:
                        phase += 0.08
                        jpg = build_frame(size, phase, state.verdict)
                        state.snapshot(jpg)
                        self.wfile.write(
                            b"--" + BOUNDARY.encode() + b"\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(jpg)).encode() + b"\r\n\r\n" + jpg + b"\r\n"
                        )
                        self.wfile.flush()
                        time.sleep(interval)
                except (BrokenPipeError, ConnectionResetError):
                    return
                return
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser(description="本地假摄像头（MJPEG + /stats），用于联调网页直播间")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--fps", type=float, default=8.0, help="推流帧率")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--verdict", default="cat", choices=("cat", "notcat", "starting"))
    args = ap.parse_args()

    state = MockState(args.verdict)
    handler = make_handler(state, (args.width, args.height), args.fps)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print("假摄像头已启动：http://%s:%d/  (verdict=%s, %dx%d@%d)"
          % (args.host, args.port, args.verdict, args.width, args.height, args.fps), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
