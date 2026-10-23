"""测试用契约对象工厂。字段名改了这里会一起改，改不动就说明契约真的变了。"""

from __future__ import annotations

from datetime import datetime, timezone

from catvision_contracts import (
    ActionEvent,
    CatFace,
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
    Quality,
    SourceInfo,
    Votes,
)

TS = datetime(2026, 10, 22, 10, 0, 0, tzinfo=timezone.utc)


def sample_frame_packet(**over) -> FramePacket:
    kwargs = dict(
        camera_id="cam0",
        seq=0,
        width=640,
        height=480,
        image_path="/dev/shm/catvision/frames/cam0/f000000.jpg",
        source=SourceInfo(kind="synthetic", uri="synthetic:1"),
        fmt="jpeg",
        image_sha1="0" * 40,
        captured_at=TS,
    )
    kwargs.update(over)
    return FramePacket.build(**kwargs)


def sample_landmarks(**over) -> Landmarks:
    kwargs = dict(
        left_eye=[200.0, 220.0],
        right_eye=[280.0, 220.0],
        nose=[240.0, 260.0],
        left_ear_base=[195.0, 180.0],
        right_ear_base=[285.0, 180.0],
        left_ear_tip=[180.0, 150.0],
        right_ear_tip=[300.0, 150.0],
    )
    kwargs.update(over)
    return Landmarks(**kwargs)


def sample_cat_face(*, landmarks: Landmarks | None = None, **over) -> CatFace:
    """构造一个合法 CatFace。

    注意：landmarks 的字段（left_ear_tip 之类）不能直接当 kwargs 传进来，
    因为 CatFace 是 extra="forbid" —— 传错层级会报 extra_forbidden。
    要改关键点请用 landmarks=sample_landmarks(left_ear_tip=None)。
    """
    kwargs = dict(
        packet_id="cam0-20261022T100000.000-000000",
        track_id="t-0001",
        bbox=[180.0, 160.0, 120.0, 140.0],
        det_score=0.93,
        landmarks=landmarks or sample_landmarks(),
        head_pose=HeadPose(yaw=3.0, pitch=-1.0, roll=0.5),
        identity=Identity(
            cat_id="cat-001",
            name="大橘",
            similarity=0.88,
            decision="matched",
            gallery_version="g-2026w42",
        ),
        quality=Quality(blur=120.0, brightness=140.0, is_usable=True),
    )
    kwargs.update(over)
    return CatFace(**kwargs)


def sample_ear_notch(*, left: EarSide | None = None, right: EarSide | None = None, **over) -> EarNotch:
    left = left or EarSide(visible=True, notched=True, score=0.91, bbox=[180.0, 150.0, 40.0, 40.0])
    right = right or EarSide(visible=True, notched=False, score=0.88, bbox=[280.0, 150.0, 40.0, 40.0])
    kwargs = dict(
        packet_id="cam0-20261022T100000.000-000000",
        track_id="t-0001",
        left=left,
        right=right,
        rule="any_ear_notched",
        model_version="earnotch-v0.1",
    )
    kwargs.update(over)
    return EarNotch.from_ears(**kwargs)


def sample_detection_event(**over) -> DetectionEvent:
    kwargs = dict(
        event_id="det-abc123",
        emitted_at=TS,
        camera_id="cam0",
        track_id="t-0001",
        cat=EventCat(cat_id="cat-001", name="大橘", similarity=0.88, decision="matched"),
        neutered=EventNeutered(value=True, confidence=0.91),
        votes=Votes(identity={"cat-001": 8}, ear={"neutered": 8}),
        evidence=Evidence(
            frames_seen=8,
            concurrent_tracks=1,
            first_seen=TS,
            last_seen=TS,
            best_frame_path="/dev/shm/catvision/frames/cam0/f000003.jpg",
        ),
    )
    kwargs.update(over)
    return DetectionEvent(**kwargs)


def sample_action_event(**over) -> ActionEvent:
    kwargs = dict(
        event_id="act-abc123",
        emitted_at=TS,
        type="FEED_DISPENSE",
        track_id="t-0001",
        cat_id="cat-001",
        reason="识别到已建档猫 cat-001",
        payload={"portion_g": 30, "dry_run": True},
        status="skipped",
    )
    kwargs.update(over)
    return ActionEvent(**kwargs)
