"""CatVision v1 契约模型（pydantic v2）。

契约的权威定义是 contracts/v1/*.schema.json，这里是 Python 绑定。
两边必须保持一致，tests/contract/ 会同时校验。

改动流程：改 schema + 改本文件 + 更新 contracts/CHANGELOG.md + PR。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FRAME_PACKET = "catvision.frame_packet/1.0"
CAT_FACE = "catvision.cat_face/1.0"
EAR_NOTCH = "catvision.ear_notch/1.0"
DETECTION_EVENT = "catvision.detection_event/1.0"
ACTION_EVENT = "catvision.action_event/1.0"


def utcnow() -> datetime:
    """带时区的当前时间（契约里所有时间都必须是 aware datetime）。"""
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class ContractBase(BaseModel):
    """所有契约对象的基类。

    - extra="forbid"：多写一个字段直接报错（防止拼错字段名悄悄过去）
    - populate_by_name：允许用字段名或 alias 构造
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        return cls.model_validate(data)


# --------------------------------------------------------------------------- #
# 1. FramePacket  ——  摄像头模块 → 猫脸 / 耳标模块
# --------------------------------------------------------------------------- #


class SourceInfo(ContractBase):
    kind: Literal["csi", "usb", "rtsp", "file", "synthetic"]
    uri: str


class FramePacket(ContractBase):
    """一帧图像 + 元数据。只给图片路径，不内联图像数据。"""

    schema_: Literal["catvision.frame_packet/1.0"] = Field(default=FRAME_PACKET, alias="schema")
    packet_id: str
    camera_id: str
    captured_at: datetime
    seq: int = Field(ge=0)
    width: int = Field(ge=1)
    height: int = Field(ge=1)
    format: Literal["jpeg", "png"]
    image_path: str
    image_sha1: str | None = None
    source: SourceInfo

    @classmethod
    def build(
        cls,
        *,
        camera_id: str,
        seq: int,
        width: int,
        height: int,
        image_path: str,
        source: SourceInfo,
        fmt: str = "jpeg",
        image_sha1: str | None = None,
        captured_at: datetime | None = None,
        packet_id: str | None = None,
    ) -> FramePacket:
        ts = captured_at or utcnow()
        pid = packet_id or f"{camera_id}-{ts.strftime('%Y%m%dT%H%M%S.%f')[:-3]}-{seq:06d}"
        return cls(
            packet_id=pid,
            camera_id=camera_id,
            captured_at=ts,
            seq=seq,
            width=width,
            height=height,
            format=fmt,
            image_path=str(image_path),
            image_sha1=image_sha1,
            source=source,
        )


# --------------------------------------------------------------------------- #
# 2. CatFace  ——  猫脸模块 → 耳标模块 / 决策层
# --------------------------------------------------------------------------- #


class Landmarks(ContractBase):
    """7 个关键点。耳标模块的耳部 ROI 裁剪完全依赖这些点。

    耳尖不可见时必须显式给 null，不要瞎填坐标。
    """

    left_eye: list[float]
    right_eye: list[float]
    nose: list[float]
    left_ear_base: list[float]
    right_ear_base: list[float]
    left_ear_tip: list[float] | None = None
    right_ear_tip: list[float] | None = None


class HeadPose(ContractBase):
    yaw: float
    pitch: float
    roll: float


class Identity(ContractBase):
    cat_id: str | None
    name: str | None
    similarity: float | None
    decision: Literal["matched", "unknown", "ambiguous"]
    gallery_version: str


class Quality(ContractBase):
    blur: float
    brightness: float
    is_usable: bool


class CatFace(ContractBase):
    schema_: Literal["catvision.cat_face/1.0"] = Field(default=CAT_FACE, alias="schema")
    packet_id: str
    track_id: str
    bbox: list[float]           # [x, y, w, h]
    det_score: float = Field(ge=0, le=1)
    landmarks: Landmarks
    head_pose: HeadPose
    identity: Identity
    quality: Quality

    @property
    def x(self) -> float:
        return self.bbox[0]

    @property
    def y(self) -> float:
        return self.bbox[1]

    @property
    def w(self) -> float:
        return self.bbox[2]

    @property
    def h(self) -> float:
        return self.bbox[3]


# --------------------------------------------------------------------------- #
# 3. EarNotch  ——  耳标模块 → 决策层
# --------------------------------------------------------------------------- #


class EarSide(ContractBase):
    visible: bool
    notched: bool | None
    score: float | None
    bbox: list[float] | None

    @model_validator(mode="after")
    def _enforce_visible_rule(self) -> EarSide:
        if not self.visible and (self.notched is not None or self.score is not None):
            raise ValueError("契约违规：visible=false 时 notched 和 score 必须为 null（看不见就说看不见，禁止猜）")
        return self


class NeuteredVerdict(ContractBase):
    value: bool | None
    source: Literal["ear_notch"] = "ear_notch"
    confidence: float | None = None
    rule: Literal["any_ear_notched", "both_ears_notched", "left_only", "right_only"] = "any_ear_notched"


class EarNotch(ContractBase):
    """剪耳结果。剪耳=已绝育/已TNR；未剪耳=疑似未绝育。"""

    schema_: Literal["catvision.ear_notch/1.0"] = Field(default=EAR_NOTCH, alias="schema")
    packet_id: str
    track_id: str
    left: EarSide
    right: EarSide
    neutered: NeuteredVerdict
    model_version: str

    @classmethod
    def from_ears(
        cls,
        *,
        packet_id: str,
        track_id: str,
        left: EarSide,
        right: EarSide,
        rule: str = "any_ear_notched",
        model_version: str = "unknown",
    ) -> EarNotch:
        """按规则把左右耳结果合成绝育结论（规则是配置项，不是模型输出）。"""
        judged = [e for e in (left, right) if e.visible and e.notched is not None]
        value: bool | None = None
        conf: float | None = None

        if judged:
            if rule == "any_ear_notched":
                value = any(bool(e.notched) for e in judged)
            elif rule == "both_ears_notched":
                value = all(bool(e.notched) for e in judged) and len(judged) == 2
            elif rule == "left_only":
                value = bool(left.notched) if left.visible and left.notched is not None else None
            elif rule == "right_only":
                value = bool(right.notched) if right.visible and right.notched is not None else None
            if value is not None:
                conf = max((e.score or 0.0) for e in judged)

        return cls(
            packet_id=packet_id,
            track_id=track_id,
            left=left,
            right=right,
            neutered=NeuteredVerdict(value=value, confidence=conf, rule=rule),
            model_version=model_version,
        )


# --------------------------------------------------------------------------- #
# 4. DetectionEvent  ——  决策层 → 前端（聚合后）
# --------------------------------------------------------------------------- #


class EventCat(ContractBase):
    cat_id: str | None
    name: str | None
    similarity: float | None
    decision: Literal["matched", "unknown", "ambiguous"]


class EventNeutered(ContractBase):
    value: bool | None
    confidence: float | None


class Votes(ContractBase):
    identity: dict[str, int]
    ear: dict[str, int]


class Evidence(ContractBase):
    frames_seen: int
    concurrent_tracks: int = 1
    first_seen: datetime
    last_seen: datetime
    best_frame_path: str | None = None
    snapshot_url: str | None = None


class DetectionEvent(ContractBase):
    schema_: Literal["catvision.detection_event/1.0"] = Field(default=DETECTION_EVENT, alias="schema")
    event_id: str
    emitted_at: datetime
    camera_id: str
    track_id: str
    cat: EventCat
    neutered: EventNeutered
    votes: Votes
    evidence: Evidence


# --------------------------------------------------------------------------- #
# 5. ActionEvent  ——  投粮 / TNR / 告警
# --------------------------------------------------------------------------- #


class ActionEvent(ContractBase):
    schema_: Literal["catvision.action_event/1.0"] = Field(default=ACTION_EVENT, alias="schema")
    event_id: str
    emitted_at: datetime
    type: Literal["FEED_DISPENSE", "TNR_TASK_CREATED", "ALERT"]
    track_id: str | None
    cat_id: str | None
    reason: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: Literal["queued", "executed", "failed", "skipped"] = "queued"
