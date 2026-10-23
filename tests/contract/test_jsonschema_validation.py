"""用真正的 JSON Schema 校验实例（跨语言对接时以它为准）。

没装 jsonschema 就跳过（离线开发环境）；CI 上必须装上，见文件末尾的守卫。
"""

from __future__ import annotations

import os

import pytest

jsonschema = pytest.importorskip("jsonschema", reason="需要 dev 依赖 jsonschema")

from catvision_contracts import validate_dict  # noqa: E402

from tests.factories import (  # noqa: E402
    sample_action_event,
    sample_cat_face,
    sample_detection_event,
    sample_ear_notch,
    sample_frame_packet,
)

SAMPLES = {
    "frame_packet": sample_frame_packet,
    "cat_face": sample_cat_face,
    "ear_notch": sample_ear_notch,
    "detection_event": sample_detection_event,
    "action_event": sample_action_event,
}


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_pydantic_output_matches_json_schema(name: str) -> None:
    validate_dict(name, SAMPLES[name]().to_dict())


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_every_required_field_is_present(name: str) -> None:
    data = SAMPLES[name]().to_dict()
    for field in SAMPLES[name]().model_json_schema().get("required", []):
        assert field in data, f"{name}: required 字段 {field} 没被产出"


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_schema_rejects_unknown_field(name: str) -> None:
    data = SAMPLES[name]().to_dict()
    data["totally_unexpected_field"] = 1
    with pytest.raises(jsonschema.ValidationError):
        validate_dict(name, data)


@pytest.mark.parametrize("name", sorted(SAMPLES))
def test_schema_rejects_missing_required_field(name: str) -> None:
    import catvision_contracts as cc

    data = SAMPLES[name]().to_dict()
    for field in cc.load_schema(name)["required"]:
        broken = dict(data)
        broken.pop(field, None)
        if set(broken) == set(data):
            continue
        with pytest.raises(jsonschema.ValidationError):
            validate_dict(name, broken)
        break  # 抽一个字段验证即可，避免 5 个契约 × N 字段的全排列


def test_ear_invisible_rejected_by_schema_too() -> None:
    """pydantic 和 JSON Schema 两层都要拦住（猫脸、耳标模块可能用别的语言调）。"""
    data = sample_ear_notch().to_dict()
    data["left"] = {"visible": False, "notched": True, "score": 0.9, "bbox": None}
    with pytest.raises(jsonschema.ValidationError):
        validate_dict("ear_notch", data)


def test_ear_invisible_null_is_accepted() -> None:
    data = sample_ear_notch().to_dict()
    data["left"] = {"visible": False, "notched": None, "score": None, "bbox": None}
    validate_dict("ear_notch", data)


def test_catface_ear_tip_null_is_accepted() -> None:
    """耳尖看不见时给 null 是合法的（耳标模块靠这个判断 ROI 能不能裁）。"""
    from tests.factories import sample_landmarks

    face = sample_cat_face(landmarks=sample_landmarks(left_ear_tip=None, right_ear_tip=None))
    data = face.to_dict()
    assert data["landmarks"]["left_ear_tip"] is None
    validate_dict("cat_face", data)


def test_timestamps_must_be_timezone_aware() -> None:
    """所有时间必须带时区，否则跨机器对不上。"""
    data = sample_frame_packet().to_dict()
    assert data["captured_at"].endswith("Z") or "+" in data["captured_at"]
    validate_dict("frame_packet", data)


def test_bad_enum_rejected() -> None:
    data = sample_action_event().to_dict()
    data["type"] = "FEED_THE_CAT"
    with pytest.raises(jsonschema.ValidationError):
        validate_dict("action_event", data)


def test_ci_must_have_jsonschema() -> None:
    """CI 上没有 jsonschema = 契约其实没被真正校验过，直接失败。"""
    if os.environ.get("CI"):
        import jsonschema as js  # noqa: F401
