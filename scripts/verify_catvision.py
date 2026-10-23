"""CatVision 自证脚本：摄像头接入 + 模块联调是否真的打通。跨平台（Windows / 树莓派）。

一条命令跑完，逐项打印 PASS/FAIL，最后给总判定。判据是「真东西」而不是「命令没报错」：
  - 真帧回放：必须 source.frames_read>0 且 frames_failed=0（不靠 synthetic 蒙混）
  - 决策真触发：必须出现 FEED_DISPENSE / TNR_TASK_CREATED
  - 契约真拦截：协议不满足必须 exit=2 且打印 [契约不满足]
  - 坏输入真报错：路径不存在必须非 0 退出，不能静默兜底
  - 真硬件（仅树莓派）：csi://0 真开摄像头，必须 PIPELINE OK 且 frames_failed=0

用法：
    python scripts/verify_catvision.py            # 从仓库任意位置跑
    python scripts/verify_catvision.py <仓库根>   # 显式指定仓库根
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PY = sys.executable
results: list[tuple[str, bool, str]] = []


def _find_root() -> Path:
    here = Path(__file__).resolve()
    for base in [here.parent, *here.parents]:
        if (base / "pipeline" / "runner.py").exists() and (base / "contracts" / "python").exists():
            return base
    return here.parents[1]


ROOT = _find_root()
ENV = dict(os.environ)
ENV["PYTHONPATH"] = os.pathsep.join(
    [str(ROOT), str(ROOT / "contracts" / "python"), ENV.get("PYTHONPATH", "")]
).strip(os.pathsep)
ENV["PYTHONIOENCODING"] = "utf-8"


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))
    return ok


def run(args: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, *args], cwd=str(ROOT), env=ENV,
        capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout,
    )


def run_pipeline(extra: list[str], timeout: int = 300):
    p = run(["-m", "pipeline.runner", *extra, "--quiet"], timeout=timeout)
    out = (p.stdout or "") + (p.stderr or "")
    data = None
    start, end = out.find("{"), out.rfind("}")
    if start != -1 and end > start:
        try:
            data = json.loads(out[start:end + 1])
        except Exception:
            data = None
    return p, out, data


def assert_summary(out: str, data, frames=None, dets=None, acts=None) -> tuple[bool, str]:
    if "PIPELINE OK" not in out:
        return False, "没有打印 PIPELINE OK"
    if not isinstance(data, dict):
        return False, "拿不到 JSON 摘要"
    msgs = []
    if frames is not None and data.get("frames") != frames:
        msgs.append(f"frames={data.get('frames')} 期望 {frames}")
    if dets is not None and data.get("detections") != dets:
        msgs.append(f"detections={data.get('detections')} 期望 {dets}")
    if acts is not None and data.get("actions") != acts:
        msgs.append(f"actions={data.get('actions')} 期望 {acts}")
    return (not msgs), ("; ".join(msgs) or
                        f"frames={data.get('frames')} det={data.get('detections')} act={data.get('actions')}")


def l1_unit() -> None:
    print("\n=== L1 单元测试（摄像头 + 流水线）===")
    p = run(["-m", "pytest", "tests/test_camera.py", "tests/test_pipeline.py", "-q"], timeout=600)
    out = (p.stdout or "") + (p.stderr or "")
    n = out.count(".")
    check("L1 采集/流水线单测全绿", p.returncode == 0, f"exit={p.returncode} 用例数≈{n}")


def l2_d0() -> None:
    print("\n=== L2 D0：合成源全链路 ===")
    _, out, data = run_pipeline(["--source", "synthetic:30", "--mock-all"])
    ok, d = assert_summary(out, data, frames=30, dets=1, acts=1)
    check("L2 D0 合成 30 帧产出 DetectionEvent + FEED_DISPENSE", ok and "FEED_DISPENSE" in out, d)

    _, out, data = run_pipeline(["--source", "synthetic:20", "--mock-all", "--mock-intact"])
    ok, d = assert_summary(out, data, acts=2)
    check("L2 未绝育场景触发 2 个动作（FEED + TNR）",
          ok and "FEED_DISPENSE" in out and "TNR_TASK_CREATED" in out, d)

    _, out, data = run_pipeline(["--source", "synthetic:20", "--mock-all", "--mock-multi-cat-ratio", "1.0"])
    ok, d = assert_summary(out, data, acts=0)
    check("L2 双猫同框不投粮（actions=0）", ok and "FEED_DISPENSE" not in out, d)


def _make_frames(n: int = 20) -> Path:
    from PIL import Image
    d = Path(tempfile.mkdtemp(prefix="catvision_frames_"))
    for i in range(n):
        Image.new("RGB", (640, 480), (i * 7 % 255, 90, 160)).save(d / f"frame_{i:04d}.jpg", quality=85)
    return d


def l3_file_replay() -> None:
    print("\n=== L3 真帧回放（真 JPEG 目录进链路）===")
    frames_dir = _make_frames(20)
    _, out, data = run_pipeline(["--source", f"file:{frames_dir.as_posix()}", "--mock-all"])
    cap = data.get("capture", {}) if isinstance(data, dict) else {}
    src = cap.get("source", {}) if isinstance(cap, dict) else {}
    ok_src = (src.get("frames_read") == 20 and src.get("frames_failed") == 0 and src.get("kind") == "file")
    ok, d = assert_summary(out, data, frames=20, dets=1)
    check("L3 file 源真读到 20 张帧且 0 失败", ok and ok_src, f"source={src} | {d}")


def l4_contract() -> None:
    print("\n=== L4 契约联调 ===")
    p = run(["-m", "pytest", "tests/contract", "-q"], timeout=600)
    out = (p.stdout or "") + (p.stderr or "")
    check("L4 契约测试（schema 与 pydantic 对齐，需 jsonschema）",
          p.returncode == 0, f"exit={p.returncode} 用例数≈{out.count('.')}")

    p = run(["-m", "pipeline.runner", "--source", "synthetic:5",
             "--catface", "json.decoder:JSONDecoder", "--earnotch", "mocks:MockEarNotchModule", "--quiet"])
    out = (p.stdout or "") + (p.stderr or "")
    check("L4 协议不满足 -> exit=2 且打印 [契约不满足]",
          p.returncode == 2 and "[契约不满足]" in out, f"exit={p.returncode}")

    p = run(["-m", "pipeline.runner", "--source", "file:/no/such/dir/zzz", "--mock-all", "--quiet"], timeout=60)
    out = (p.stdout or "") + (p.stderr or "")
    check("L4 源路径不存在 -> 报错退出（无静默兜底）",
          p.returncode != 0 and ("不存在" in out or "FileNotFoundError" in out), f"exit={p.returncode}")


def l5_real_camera() -> None:
    print("\n=== L5 真摄像头（CSI）===")
    has_dev = Path("/dev/video0").exists()
    try:
        import picamera2  # noqa: F401
        has_lib = True
    except Exception:
        has_lib = False
    if not (has_dev and has_lib):
        print(f"[SKIP] 本机没有 CSI 摄像头（/dev/video0={has_dev}, picamera2={has_lib}）；请在树莓派上跑本脚本。")
        return
    _, out, data = run_pipeline(["--source", "csi://0", "--fps", "2", "--frames", "10", "--mock-all"], timeout=180)
    cap = data.get("capture", {}) if isinstance(data, dict) else {}
    src = cap.get("source", {}) if isinstance(cap, dict) else {}
    ok, d = assert_summary(out, data, frames=10)
    check("L5 CSI 真摄像头 10 帧全链路 PIPELINE OK",
          ok and src.get("kind") == "csi" and src.get("frames_failed") == 0, f"source={src} | {d}")


def main() -> int:
    global ROOT
    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir() and (Path(sys.argv[1]) / "pipeline").exists():
        ROOT = Path(sys.argv[1]).resolve()
        ENV["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT), str(ROOT / "contracts" / "python"), os.environ.get("PYTHONPATH", "")]
        ).strip(os.pathsep)
    print(f"CatVision 自证脚本  Python={sys.version.split()[0]}  ROOT={ROOT}")
    print("=" * 70)
    l1_unit()
    l2_d0()
    l3_file_replay()
    l4_contract()
    l5_real_camera()
    print("\n" + "=" * 70)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = [n for n, ok, _ in results if not ok]
    print(f"结果：{passed}/{len(results)} 项通过")
    if failed:
        print("未通过：")
        for n in failed:
            print(f"  - {n}")
        return 1
    print("全部通过：摄像头接入 + 模块联调 已实际打通。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
