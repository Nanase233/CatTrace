#!/usr/bin/env python3
"""模型导出占位（猫脸、耳标模块用）。

统一约定：导出成 ONNX，放 models/<模块>/<名字>_v<版本>.onnx，
并在 models/MANIFEST.json 登记。树莓派上**不要**用 TFLite
（实测 Py3.13 aarch64 没有 tflite-runtime 的 wheel，这条路是死的）。

    python scripts/export_onnx.py --check models/catface/m1_v0.1.onnx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def check(path: Path) -> int:
    if not path.exists():
        print(f"找不到模型：{path}")
        return 1
    try:
        import onnxruntime as ort
    except ImportError:
        print("没装 onnxruntime（Pi 上：pip install onnxruntime）")
        return 2
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    print(f"OK {path.name}")
    for i in sess.get_inputs():
        print(f"  in  {i.name:24s} {i.shape} {i.type}")
    for o in sess.get_outputs():
        print(f"  out {o.name:24s} {o.shape} {o.type}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="要检查的 .onnx")
    ap.add_argument("--manifest", action="store_true", help="打印 models/MANIFEST.json")
    args = ap.parse_args()

    if args.manifest:
        root = Path(__file__).resolve().parents[1] / "models" / "MANIFEST.json"
        if root.exists():
            print(json.dumps(json.loads(root.read_text(encoding="utf-8")), ensure_ascii=False, indent=2))
        else:
            print("还没有 models/MANIFEST.json")
        return 0

    if not args.path:
        ap.print_help()
        return 1
    return check(Path(args.path))


if __name__ == "__main__":
    raise SystemExit(main())
