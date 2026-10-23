"""CatVision v1 契约：唯一权威接口定义的 Python 绑定。"""

from .interfaces import CatFaceModule, EarNotchModule
from .models import (
    ACTION_EVENT,
    CAT_FACE,
    DETECTION_EVENT,
    EAR_NOTCH,
    FRAME_PACKET,
    ActionEvent,
    CatFace,
    ContractBase,
    DetectionEvent,
    EarNotch,
    EarSide,
    EventCat,
    EventNeutered,
    Evidence,
    FramePacket,
    HeadPose,
    Identity,
    Landmarks,
    NeuteredVerdict,
    Quality,
    SourceInfo,
    Votes,
    new_id,
    utcnow,
)
from .validate import (
    SCHEMA_DIR,
    SCHEMAS,
    ShapeError,
    check_shape,
    load_schema,
    resolve_ref,
    validate,
    validate_dict,
)

__all__ = [
    "ACTION_EVENT", "CAT_FACE", "DETECTION_EVENT", "EAR_NOTCH", "FRAME_PACKET",
    "ActionEvent", "CatFace", "ContractBase", "DetectionEvent", "EarNotch", "EarSide",
    "Evidence", "EventCat", "EventNeutered", "FramePacket", "HeadPose", "Identity",
    "Landmarks", "NeuteredVerdict", "Quality", "SourceInfo", "Votes",
    "new_id", "utcnow",
    "SCHEMAS", "SCHEMA_DIR", "ShapeError", "check_shape", "load_schema",
    "resolve_ref", "validate", "validate_dict",
    "CatFaceModule", "EarNotchModule",
]
