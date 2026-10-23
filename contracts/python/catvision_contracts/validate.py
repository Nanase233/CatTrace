"""契约校验。

两层：

1. ``check_shape``  —— 零依赖的形状检查：必填项、多余字段、const/enum、嵌套对象。
   树莓派上少一个依赖就少一份风险，本地快速自检 / 老版本环境用它。

2. ``validate_dict`` —— 完整的 JSON Schema 校验（需要 jsonschema）。
   跨语言对接、CI、契约变更时以它为准，因为 JSON Schema 才是最终裁判。
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "v1"

SCHEMAS = {
    "frame_packet": "frame_packet.schema.json",
    "cat_face": "cat_face.schema.json",
    "ear_notch": "ear_notch.schema.json",
    "detection_event": "detection_event.schema.json",
    "action_event": "action_event.schema.json",
}

SCHEMA_DIR = _SCHEMA_DIR


class ShapeError(ValueError):
    """形状不符（零依赖检查的结果）。"""


@cache
def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise KeyError(f"未知契约 {name!r}，可选：{sorted(SCHEMAS)}")
    return json.loads((_SCHEMA_DIR / SCHEMAS[name]).read_text(encoding="utf-8"))


def resolve_ref(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    """跟随本地 $ref（#/$defs/xxx），只支持同文档内引用。"""
    ref = node.get("$ref")
    if not ref:
        return node
    if not ref.startswith("#/"):
        raise ShapeError(f"不支持外部 $ref：{ref}")
    cur: Any = schema
    for part in ref[2:].split("/"):
        cur = cur[part]
    return cur


def check_shape(name: str, data: Any, *, path: str = "") -> None:
    """零依赖的结构检查。不符合就抛 ShapeError。"""
    schema = load_schema(name)
    _check(schema, schema, data, path or name)


def _check(schema: dict[str, Any], node: dict[str, Any], data: Any, path: str) -> None:
    node = resolve_ref(schema, node)

    if "const" in node:
        if data != node["const"]:
            raise ShapeError(f"{path}: 期望常量 {node['const']!r}，实际 {data!r}")
        return

    if "enum" in node:
        if data not in node["enum"]:
            raise ShapeError(f"{path}: 期望 {node['enum']} 之一，实际 {data!r}")
        return

    types = node.get("type")
    if isinstance(types, str):
        types = [types]
    if types and data is None and "null" not in types:
        raise ShapeError(f"{path}: 不允许为 null")
    if types and data is not None:
        py_ok = {
            "object": isinstance(data, dict),
            "array": isinstance(data, list),
            "string": isinstance(data, str),
            "integer": isinstance(data, int) and not isinstance(data, bool),
            "number": isinstance(data, (int, float)) and not isinstance(data, bool),
            "boolean": isinstance(data, bool),
            "null": data is None,
        }
        if not any(py_ok.get(t, False) for t in types):
            raise ShapeError(f"{path}: 类型应为 {types}，实际 {type(data).__name__}")

    if isinstance(data, dict) and node.get("type") in ("object", None) and "properties" in node:
        props = node["properties"]
        for key in node.get("required", []):
            if key not in data:
                raise ShapeError(f"{path}: 缺少必填字段 {key!r}")
        if node.get("additionalProperties") is False:
            extra = set(data) - set(props)
            if extra:
                raise ShapeError(f"{path}: 出现未定义字段 {sorted(extra)}")
        for key, value in data.items():
            if key in props:
                _check(schema, props[key], value, f"{path}.{key}")

    # 条件约束（ear_notch 的 visible=false 规则）
    for clause in node.get("allOf", []):
        if "if" in clause:
            if _matches(schema, clause["if"], data):
                _check(schema, clause.get("then", {}), data, path)
        else:
            _check(schema, clause, data, path)


def _matches(schema: dict[str, Any], cond: dict[str, Any], data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for key in cond.get("required", []):
        if key not in data:
            return False
    for key, sub in (cond.get("properties") or {}).items():
        if key not in data:
            continue
        if "const" in sub and data[key] != sub["const"]:
            return False
        if "enum" in sub and data[key] not in sub["enum"]:
            return False
    return True


def validate_dict(name: str, data: dict[str, Any]) -> None:
    """完整 JSON Schema 校验。不符合就抛 jsonschema.ValidationError。"""
    import jsonschema

    jsonschema.validate(instance=data, schema=load_schema(name))


def validate(name: str, obj) -> None:
    """接受契约对象或 dict，先用零依赖检查，若装了 jsonschema 再全量校验。"""
    data = obj.to_dict() if hasattr(obj, "to_dict") else obj
    check_shape(name, data)
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        return
    validate_dict(name, data)
