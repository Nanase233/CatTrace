"""D0 验收：一条命令跑通「摄像头 -> 猫脸 -> 剪耳 -> 决策 -> 事件」。

    python -m pipeline.runner --source synthetic:60 --mock-all

这条命令跑通（打印 PIPELINE OK + DetectionEvent）之前，谁都不许开始写模型。
理由：契约 + Mock + 数据管道是第一周唯一的交付物，模型晚一天不致命，
接口对不上会让三个模块互相卡死。

换真实现时只改一个参数：
    --catface modules.catface:M1CatFaceModule    （猫脸模块的实现）
    --earnotch modules.earnotch:EarNotchModule   （耳标模块的实现）
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
import time
from datetime import datetime, timezone

from catvision_contracts import CatFaceModule, EarNotchModule

from .aggregate import TrackAggregator
from .bus import EventBus
from .decide import DecisionConfig, DecisionEngine
from .store import Store

log = logging.getLogger("catvision.pipeline")


# --------------------------------------------------------------------------- #
# 模块加载：mock 或真实现
# --------------------------------------------------------------------------- #
def load_module(spec: str):
    """支持 "pkg.mod:Class" 或 "pkg.mod.Class"。

    额外支持构造参数："pkg.mod:Class?k=v&k2=v2"
    """
    if ":" not in spec:
        mod_name, _, cls_name = spec.rpartition(".")
        if not mod_name:
            raise ValueError(f"模块标识要写成 pkg.mod:Class 或 pkg.mod.Class，收到 {spec!r}")
    else:
        mod_name, cls_name = spec.split(":", 1)
        cls_name = cls_name.split("?", 1)[0]
    kwargs: dict = {}
    if "?" in spec:
        query = spec.split("?", 1)[1]
        for pair in query.split("&"):
            if not pair:
                continue
            k, _, v = pair.partition("=")
            if v.lower() in ("true", "false"):
                kwargs[k] = v.lower() == "true"
            else:
                try:
                    kwargs[k] = int(v)
                except ValueError:
                    kwargs[k] = v
    mod = importlib.import_module(mod_name)
    cls = getattr(mod, cls_name)
    return cls(**kwargs)


def resolve_modules(args):
    if args.mock_all:
        from mocks import MockCatFaceModule, MockEarNotchModule

        face = MockCatFaceModule(seed=args.seed, multi_cat_ratio=args.mock_multi_cat_ratio)
        # 默认左耳已剪（TNR 的典型结果）→ 不该触发 TNR 任务；
        # 加 --mock-intact 变成未绝育 → 应该触发 TNR，用来验证告警链路。
        ear = MockEarNotchModule(
            seed=args.seed + 1,
            notched_left=not args.mock_intact,
            notched_right=False,
        )
        return face, ear
    if not args.catface or not args.earnotch:
        raise SystemExit(
            "要么加 --mock-all，要么同时给 --catface 和 --earnotch。\n"
            "  例：--catface modules.catface:M1CatFaceModule --earnotch modules.earnotch:EarNotchModule"
        )
    return load_module(args.catface), load_module(args.earnotch)


def check_protocol(face, ear) -> list[str]:
    """下游必须能按协议调用；不满足就早失败，别等跑起来才炸。"""
    problems = []
    if not isinstance(face, CatFaceModule):
        problems.append(f"{type(face).__name__} 不满足 CatFaceModule 协议（缺 analyze(packet) -> list[CatFace]）")
    if not isinstance(ear, EarNotchModule):
        problems.append(f"{type(ear).__name__} 不满足 EarNotchModule 协议（缺 analyze(packet, faces) -> list[EarNotch]）")
    return problems


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m pipeline.runner", description="CatVision 主流水线")
    p.add_argument("--source", default="synthetic:60", help="csi://0 | file:/path | rtsp://... | synthetic:N")
    p.add_argument("--fps", type=float, default=3.0)
    p.add_argument("--frames", type=int, default=0, help="最多处理多少帧（0=由源决定）")
    p.add_argument("--camera-id", default="cam0")
    p.add_argument("--frame-root", default=None)
    p.add_argument("--keep-frames", type=int, default=120)
    p.add_argument("--loop", action="store_true")

    p.add_argument("--mock-all", action="store_true", help="猫脸 + 剪耳都用 Mock（D0 验收用这个）")
    p.add_argument(
        "--mock-intact",
        action="store_true",
        help="Mock 剪耳：两只耳朵都完整（未绝育）。默认是左耳已剪，用来演示 TNR 不触发。",
    )
    p.add_argument("--mock-multi-cat-ratio", type=float, default=0.0, help="Mock 双猫同框概率，验证「不投粮」")
    p.add_argument("--seed", type=int, default=20261022)
    p.add_argument("--catface", default=None, help="猫脸模块的模块：pkg.mod:Class")
    p.add_argument("--earnotch", default=None, help="耳标模块的模块：pkg.mod:Class")

    p.add_argument("--db", default=None, help="SQLite 路径（默认不落盘，纯内存）")
    p.add_argument("--jsonl", default=None, help="把事件同时写 JSONL")
    p.add_argument("--real-feed", action="store_true", help="真的触发投粮（默认 dry-run）")
    p.add_argument("--track-timeout", type=float, default=3.0)
    p.add_argument("--quiet", action="store_true", help="只打印最终结果")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not args.quiet:
        log.setLevel(logging.WARNING)

    face_mod, ear_mod = resolve_modules(args)
    problems = check_protocol(face_mod, ear_mod)
    if problems:
        for p in problems:
            print(f"[契约不满足] {p}", file=sys.stderr)
        return 2

    from modules.camera.capture import CameraStream

    store = Store(args.db) if args.db else Store(":memory:")
    bus = EventBus()
    if args.jsonl:
        bus.to_jsonl(args.jsonl)

    agg = TrackAggregator(track_timeout=args.track_timeout)
    engine = DecisionEngine(
        DecisionConfig(dry_run=not args.real_feed, feed_requires_single_cat=True),
        store=store,
    )

    t0 = time.monotonic()
    frame_count = 0
    cam_stats: dict = {}

    try:
        with CameraStream(
            args.source,
            fps=args.fps,
            camera_id=args.camera_id,
            frame_root=args.frame_root,
            keep_frames=args.keep_frames,
            loop=args.loop,
        ) as cam:
            if not args.quiet:
                print(
                    f"[camera] {cam.source.uri}  {cam.source.width}x{cam.source.height}  "
                    f"mode={cam.source.kind}  fps={args.fps}",
                    file=sys.stderr,
                )
            for packet in cam.packets(max_frames=args.frames):
                frame_count += 1

                faces = face_mod.analyze(packet)
                ears = ear_mod.analyze(packet, faces)
                agg.update(packet, faces, ears)

                # 每帧都检查有没有猫离开画面；离开就出事件
                for ev in agg.flush_stale(datetime.now(timezone.utc)):
                    _emit(ev, bus, engine, store)

                if not args.quiet and frame_count % 10 == 0:
                    print(
                        f"[{frame_count:4d}] tracks={agg.active_tracks} faces={len(faces)} "
                        f"ears={len(ears)} {cam.meter}",
                        file=sys.stderr,
                    )

            for ev in agg.flush_all():
                _emit(ev, bus, engine, store)

            cam_stats = cam.stats_dict()
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130
    finally:
        bus.close()

    elapsed = time.monotonic() - t0
    _report(args, frame_count, elapsed, bus, store, cam_stats)

    return 0 if frame_count > 0 else 1


def _emit(event, bus: EventBus, engine: DecisionEngine, store: Store) -> None:
    bus.publish(event)
    store.record_detection(event)
    for action in engine.decide(event):
        bus.publish(action)
        store.record_action(action)


def _report(args, frames: int, elapsed: float, bus: EventBus, store: Store, cam_stats: dict) -> None:
    dets = bus.detections
    acts = bus.actions

    if not args.quiet:
        print("", file=sys.stderr)
        print("=== 识别事件 (DetectionEvent) ===", file=sys.stderr)
    for ev in dets:
        line = (
            f"  track={ev.track_id} cat={ev.cat.cat_id}({ev.cat.decision},sim={ev.cat.similarity}) "
            f"neutered={ev.neutered.value}(conf={ev.neutered.confidence}) "
            f"frames={ev.evidence.frames_seen} concurrent={ev.evidence.concurrent_tracks}"
        )
        if args.quiet:
            print(line.strip())
        else:
            print(line, file=sys.stderr)
    if not args.quiet:
        print("=== 动作事件 (ActionEvent) ===", file=sys.stderr)
    for ev in acts:
        line = f"  {ev.type} status={ev.status} cat={ev.cat_id} reason={ev.reason}"
        if args.quiet:
            print(line.strip())
        else:
            print(line, file=sys.stderr)

    summary = {
        "frames": frames,
        "elapsed_s": round(elapsed, 2),
        "pipeline_fps": round(frames / elapsed, 2) if elapsed > 0 else 0.0,
        "detections": len(dets),
        "actions": len(acts),
        "capture": cam_stats,
        "db": store.counts(),
    }
    stream = sys.stdout if args.quiet else sys.stderr
    print("", file=stream)
    print(json.dumps(summary, ensure_ascii=False, indent=2), file=stream)
    print("", file=stream)
    print(f"PIPELINE OK  frames={frames}  detections={len(dets)}  actions={len(acts)}  "
          f"elapsed={elapsed:.2f}s", file=stream)


if __name__ == "__main__":
    raise SystemExit(main())
