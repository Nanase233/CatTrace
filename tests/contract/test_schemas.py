"""契约测试：JSON Schema 与 pydantic 绑定必须逐字段对齐。

这是三个模块之间唯一的「防呆网」。谁改字段不打招呼，CI 立刻红。

本文件**不依赖 jsonschema 库**（离线 / 树莓派上也能跑），
它直接比对 schema 文档里的字段名和 pydantic 模型的字段名 —— 这比对样例做校验更狠，
因为它能抓到「schema 叫 x，代码叫 y」这种最难发现的漂移。

真正的 JSON Schema 实例校验证在 test_jsonschema_validation.py。
"""

from __future__ import annotations

import pytest
from catvision_contracts import (
    ActionEvent,
    CatFace,
    DetectionEvent,
    EarNotch,
    EarSide,
    FramePacket,
    load_schema,
    resolve_ref,
)

from tests.factories import (
    sample_action_event,
    sample_cat_face,
    sample_detection_event,
    sample_ear_notch,
    sample_frame_packet,
)

MODELS = {
    "frame_packet": (FramePacket, ["source"]),
    "cat_face": (CatFace, ["landmarks", "head_pose", "identity", "quality"]),
    "ear_notch": (EarNotch, ["left", "right", "neutered"]),
    "detection_event": (DetectionEvent, ["cat", "neutered", "votes", "evidence"]),
    "action_event": (ActionEvent, []),
}

SAMPLES = {
    "frame_packet": sample_frame_packet,
    "cat_face": sample_cat_face,
    "ear_notch": sample_ear_notch,
    "detection_event": sample_detection_event,
    "action_event": sample_action_event,
}


def _names(model) -> set[str]:
    """模型的对外字段名（alias 优先，因为契约用的是 alias）。"""
    return {(f.alias or name) for name, f in model.model_fields.items()}


def _model_required(model) -> set[str]:
    return {(f.alias or name) for name, f in model.model_fields.items() if f.is_required()}


# --------------------------------------------------------------------------- #
# 结构对齐
# --------------------------------------------------------------------------- #


def test_models_cover_all_schemas() -> None:
    """5 个契约一个都不能少。漏一个 = 链路上有个环节没有定义。"""
    from catvision_contracts import SCHEMAS

    assert set(SCHEMAS) == set(MODELS), "contracts/v1 里的 schema 和测试清单不一致"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_schema_and_model_fields_match(name: str) -> None:
    model, _ = MODELS[name]
    schema = load_schema(name)
    assert set(schema["properties"]) == _names(model), (
        f"{name}: schema 字段与 pydantic 字段不一致。"
        f" schema={sorted(schema['properties'])} model={sorted(_names(model))}"
    )


@pytest.mark.parametrize("name", sorted(MODELS))
def test_schema_is_at_least_as_strict_as_model(name: str) -> None:
    """代码认为必填的，schema 必须也必填（方向不能反）。"""
    model, _ = MODELS[name]
    missing = _model_required(model) - set(load_schema(name)["required"])
    assert not missing, f"{name}: 代码必填但 schema 没要求：{sorted(missing)}"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_schema_required_fields_are_always_emitted(name: str) -> None:
    """schema 要求了的字段，pydantic 必须每次都产出（可以有默认值，但不能漏）。"""
    data = SAMPLES[name]().to_dict()
    missing = [f for f in load_schema(name)["required"] if f not in data]
    assert not missing, f"{name}: schema 要求但 pydantic 没产出：{missing}"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_schema_forbids_extra_properties(name: str) -> None:
    """additionalProperties=false 是所有契约的硬约定：不许偷偷加字段。"""
    assert load_schema(name).get("additionalProperties") is False


@pytest.mark.parametrize("name", sorted(MODELS))
def test_nested_objects_also_forbid_extra(name: str) -> None:
    schema = load_schema(name)
    for key in MODELS[name][1]:
        assert key in schema["properties"], f"{name}: schema 里没有子对象 {key}"
        sub = resolve_ref(schema, schema["properties"][key])
        if sub.get("type") == "object":
            assert sub.get("additionalProperties") is False, f"{name}.{key} 允许了额外字段"


@pytest.mark.parametrize("name", sorted(MODELS))
def test_nested_object_fields_match_model(name: str) -> None:
    """子对象（landmarks / identity / evidence ...）字段名也要对齐。"""
    model, nested = MODELS[name]
    schema = load_schema(name)
    for key in nested:
        sub = resolve_ref(schema, schema["properties"][key])
        if sub.get("type") != "object":
            continue
        model_fields = _names(model.model_fields[key].annotation)
        assert set(sub["properties"]) == model_fields, (
            f"{name}.{key}: schema={sorted(sub['properties'])} model={sorted(model_fields)}"
        )


def test_all_schemas_declare_the_same_draft() -> None:
    drafts = {load_schema(n).get("$schema") for n in MODELS}
    assert len(drafts) == 1, f"5 个契约用的 JSON Schema 版本不一致：{drafts}"


def test_every_schema_has_a_schema_field() -> None:
    """契约里字段叫 schema，Python 里不能叫 schema（关键字冲突），必须靠 alias。"""
    for name in MODELS:
        assert "schema" in load_schema(name)["required"]
        model = MODELS[name][0]
        assert "schema" in _names(model), f"{name}: 模型没有 alias='schema' 的判别字段"


# --------------------------------------------------------------------------- #
# 语义硬规则（不是字段名，是业务约束）
# --------------------------------------------------------------------------- #


def test_ear_invisible_must_be_null() -> None:
    """看不见的耳朵不许猜：visible=false 时 notched/score 必须为 null。"""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EarSide(visible=False, notched=True, score=None, bbox=None)

    ok = EarSide(visible=False, notched=None, score=None, bbox=None)
    assert ok.notched is None and ok.score is None


def test_schema_encodes_ear_invisible_rule() -> None:
    """这条规则必须写进 schema 本身，不能只在 Python 里拦。

    耳标模块可能用别的语言（或别的进程）交付结果，JSON Schema 才是最终裁判。
    """
    schema = load_schema("ear_notch")
    for side in ("left", "right"):
        sub = resolve_ref(schema, schema["properties"][side])
        assert "allOf" in sub, f"{side} 没有编码 visible=false 的条件约束"
        cond = sub["allOf"][0]
        assert cond["if"]["properties"]["visible"]["const"] is False
        assert cond["then"]["properties"]["notched"]["type"] == "null"
        assert cond["then"]["properties"]["score"]["type"] == "null"


def test_ear_invisible_rule_is_enforced_by_checker() -> None:
    """零依赖检查器也要拦住这条（Pi 上没装 jsonschema 时的最后一道防线）。"""
    from catvision_contracts import ShapeError, check_shape

    data = sample_ear_notch().to_dict()
    data["left"] = {"visible": False, "notched": True, "score": 0.9, "bbox": None}
    with pytest.raises(ShapeError):
        check_shape("ear_notch", data)

    data["left"] = {"visible": False, "notched": None, "score": None, "bbox": None}
    check_shape("ear_notch", data)


def test_catface_requires_seven_landmarks() -> None:
    """7 个关键点必须齐全，耳标模块的耳部 ROI 全靠它。"""
    schema = load_schema("cat_face")
    req = set(resolve_ref(schema, schema["properties"]["landmarks"])["required"])
    assert req == {
        "left_eye", "right_eye", "nose",
        "left_ear_base", "right_ear_base",
        "left_ear_tip", "right_ear_tip",
    }, f"关键点集合不对：{sorted(req)}"


def test_framepacket_carries_path_not_pixels() -> None:
    """契约明确：只给图片路径，不许内联 base64。"""
    schema = load_schema("frame_packet")
    assert "image_path" in schema["required"]
    assert "image_base64" not in schema["properties"]
    assert "image" not in schema["properties"]


def test_detection_event_exposes_concurrency() -> None:
    """多猫同框判断依赖它，缺了就没法保证「不误投粮」。"""
    schema = load_schema("detection_event")
    evidence = resolve_ref(schema, schema["properties"]["evidence"])
    assert "concurrent_tracks" in evidence["required"]


def test_action_event_types_are_closed_set() -> None:
    """动作类型是封闭集合：前端和执行器都按这个 switch。"""
    schema = load_schema("action_event")
    assert set(schema["properties"]["type"]["enum"]) == {
        "FEED_DISPENSE", "TNR_TASK_CREATED", "ALERT",
    }


def test_source_kinds_are_closed_set() -> None:
    """源类型封闭，UI 和配置都按这个列表校验。"""
    schema = load_schema("frame_packet")
    source = resolve_ref(schema, schema["properties"]["source"])
    assert set(source["properties"]["kind"]["enum"]) == {
        "csi", "usb", "rtsp", "file", "synthetic",
    }


def test_version_strings_are_pinned() -> None:
    """版本串写错 = 下游静默不兼容，必须显式测。"""
    expected = {
        "frame_packet": "catvision.frame_packet/1.0",
        "cat_face": "catvision.cat_face/1.0",
        "ear_notch": "catvision.ear_notch/1.0",
        "detection_event": "catvision.detection_event/1.0",
        "action_event": "catvision.action_event/1.0",
    }
    for name, const in expected.items():
        assert load_schema(name)["properties"]["schema"]["const"] == const
        assert SAMPLES[name]().to_dict()["schema"] == const


def test_bbox_is_xywh() -> None:
    face = sample_cat_face()
    assert len(face.bbox) == 4
    assert face.x == face.bbox[0] and face.w == face.bbox[2]
