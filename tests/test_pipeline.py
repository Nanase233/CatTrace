"""联调层单测：投票聚合 + 决策规则。

重点覆盖「不该投粮」的每一条分支——误投粮是这个项目最贵的 bug。
"""

from __future__ import annotations

from datetime import timedelta

from catvision_contracts import EarSide, EventCat, EventNeutered, Evidence

from pipeline.aggregate import TrackAggregator
from pipeline.bus import EventBus
from pipeline.decide import DecisionConfig, DecisionEngine
from pipeline.store import Store
from tests.factories import (
    TS,
    sample_cat_face,
    sample_detection_event,
    sample_ear_notch,
    sample_frame_packet,
)


def _side(notched: bool, *, visible: bool = True) -> EarSide:
    """耳朵结论的构造助手：契约禁止位置参数，这里统一一下写法。"""
    return EarSide(
        visible=visible,
        notched=None if not visible else notched,
        score=0.9 if visible else None,
        bbox=None,
    )


def _run_frames(n: int, *, face_kw=None, ear_kw=None):
    agg = TrackAggregator(track_timeout=999)
    faces, ears = [], []
    for i in range(n):
        p = sample_frame_packet(seq=i)
        f = sample_cat_face(**(face_kw or {}))
        e = sample_ear_notch(**(ear_kw or {}))
        faces.append(f)
        ears.append(e)
        agg.update(p, [f], [e])
    return agg, p, faces, ears


# --- 聚合 -------------------------------------------------------------------


def test_aggregator_emits_one_event_per_track() -> None:
    agg, *_ = _run_frames(5)
    events = agg.flush_all()
    assert len(events) == 1
    ev = events[0]
    assert ev.track_id == "t-0001"
    assert ev.evidence.frames_seen == 5
    assert ev.cat.decision == "matched"
    assert ev.cat.cat_id == "cat-001"
    assert ev.neutered.value is True


def test_aggregator_skips_low_quality() -> None:
    from catvision_contracts import Quality

    agg = TrackAggregator(track_timeout=999)
    for i in range(4):
        p = sample_frame_packet(seq=i)
        f = sample_cat_face(quality=Quality(blur=5.0, brightness=10.0, is_usable=False))
        agg.update(p, [f], [])
    assert agg.flush_all() == [], "不可用帧不该产出事件"


def test_aggregator_counts_concurrent_tracks() -> None:
    agg = TrackAggregator(track_timeout=999)
    for i in range(3):
        p = sample_frame_packet(seq=i)
        a = sample_cat_face(track_id="t-0001")
        b = sample_cat_face(track_id="t-0002")
        agg.update(p, [a, b], [])
    ev = agg.flush_track("cam0", "t-0001")
    assert ev.evidence.concurrent_tracks == 2, "多猫同框必须被记录，否则会误投粮"


def test_aggregator_unknown_when_no_match() -> None:
    from catvision_contracts import Identity

    agg = TrackAggregator(track_timeout=999)
    ident = Identity(cat_id=None, name=None, similarity=0.55, decision="unknown", gallery_version="g1")
    for i in range(2):
        p = sample_frame_packet(seq=i)
        agg.update(p, [sample_cat_face(identity=ident)], [])
    ev = agg.flush_all()[0]
    assert ev.cat.decision == "unknown" and ev.cat.cat_id is None


def test_aggregator_ambiguous_on_split_votes() -> None:
    from catvision_contracts import Identity

    agg = TrackAggregator(track_timeout=999)
    pairs = [("cat-001", 3), ("cat-002", 3)]
    seq = 0
    for cat_id, n in pairs:
        for _ in range(n):
            ident = Identity(cat_id=cat_id, name=cat_id, similarity=0.85, decision="matched", gallery_version="g1")
            agg.update(sample_frame_packet(seq=seq), [sample_cat_face(identity=ident)], [])
            seq += 1
    ev = agg.flush_all()[0]
    assert ev.cat.decision == "ambiguous", "两猫票数相近时必须承认不确定"


def test_aggregator_conflicting_ears_give_majority() -> None:
    agg = TrackAggregator(track_timeout=999)
    for i in range(3):
        agg.update(
            sample_frame_packet(seq=i),
            [sample_cat_face()],
            [sample_ear_notch(left=_side(True), right=_side(True))],
        )
    for i in range(3, 5):
        agg.update(
            sample_frame_packet(seq=i),
            [sample_cat_face()],
            [sample_ear_notch(left=_side(False), right=_side(False))],
        )
    ev = agg.flush_all()[0]
    assert ev.neutered.value is True, "3:2 应该取多数"


# --- 决策 -------------------------------------------------------------------


def _det(**over):
    kwargs = dict(
        cat=EventCat(cat_id="cat-001", name="大橘", similarity=0.88, decision="matched"),
        neutered=EventNeutered(value=True, confidence=0.91),
        evidence=Evidence(
            frames_seen=5,
            concurrent_tracks=1,
            first_seen=TS,
            last_seen=TS,
        ),
    )
    kwargs.update(over)
    return sample_detection_event(**kwargs)


def test_feed_dispense_happy_path() -> None:
    engine = DecisionEngine(DecisionConfig(dry_run=True))
    acts = engine.decide(_det())
    assert len(acts) == 1
    assert acts[0].type == "FEED_DISPENSE"
    assert acts[0].status == "queued"
    assert acts[0].payload["dry_run"] is True, "dry-run 阶段执行端不能真开电机"
    assert acts[0].payload["device"] == "dry-run"


def test_real_feed_is_queued() -> None:
    engine = DecisionEngine(DecisionConfig(dry_run=False))
    acts = engine.decide(_det())
    assert acts[0].status == "queued"
    assert acts[0].payload["dry_run"] is False


def _acts(events, kind: str):
    return [a for a in events if a.type == kind]


def test_no_feed_when_similarity_low() -> None:
    engine = DecisionEngine()
    cat = EventCat(cat_id="cat-001", name="大橘", similarity=0.55, decision="matched")
    assert _acts(engine.decide(_det(cat=cat)), "FEED_DISPENSE") == []


def test_no_feed_when_multiple_cats() -> None:
    engine = DecisionEngine()
    ev = _det()
    ev.evidence.concurrent_tracks = 2
    assert _acts(engine.decide(ev), "FEED_DISPENSE") == [], "多猫同框绝对不能投粮"


def test_no_feed_when_unknown() -> None:
    """没建档的猫不能投粮（否则整袋粮会被流浪猫吃光）。"""
    engine = DecisionEngine()
    cat = EventCat(cat_id=None, name=None, similarity=0.99, decision="unknown")
    assert _acts(engine.decide(_det(cat=cat)), "FEED_DISPENSE") == []


def test_feed_respects_six_hour_cooldown() -> None:
    store = Store(":memory:")
    engine = DecisionEngine(DecisionConfig(dry_run=True), store=store)
    first = engine.decide(_det())
    assert len(first) == 1
    store.record_action(first[0])

    engine2 = DecisionEngine(DecisionConfig(dry_run=True, debounce_seconds=0), store=store)
    second = engine2.decide(_det(track_id="t-0002"))
    assert _acts(second, "FEED_DISPENSE") == [], "6 小时内不能给同一只猫再投粮"


def test_feed_allowed_after_cooldown() -> None:
    from datetime import datetime, timezone

    store = Store(":memory:")
    old = datetime.now(timezone.utc) - timedelta(hours=7)
    store.conn.execute("INSERT INTO feed_log VALUES (?,?)", ("cat-001", old.isoformat()))
    store.conn.commit()
    engine = DecisionEngine(DecisionConfig(dry_run=True), store=store)
    assert len(_acts(engine.decide(_det()), "FEED_DISPENSE")) == 1, "超过 6 小时应允许再投"


def test_debounce_same_track() -> None:
    engine = DecisionEngine(DecisionConfig(dry_run=True))
    assert len(_acts(engine.decide(_det()), "FEED_DISPENSE")) == 1
    assert _acts(engine.decide(_det()), "FEED_DISPENSE") == [], "同一 track 10 秒内只能投一次"


def test_tnr_created_for_intact_cat() -> None:
    """已建档但未剪耳：既要投粮（它是自家猫），也要建 TNR 任务。"""
    engine = DecisionEngine()
    acts = engine.decide(_det(neutered=EventNeutered(value=False, confidence=0.9)))
    assert [a.type for a in acts] == ["FEED_DISPENSE", "TNR_TASK_CREATED"]


def test_no_tnr_when_neutered() -> None:
    engine = DecisionEngine()
    acts = engine.decide(_det(neutered=EventNeutered(value=True, confidence=0.95)))
    assert _acts(acts, "TNR_TASK_CREATED") == []


def test_no_tnr_when_low_confidence() -> None:
    """置信度不够就别惊动志愿者——误报几次志愿者就不信这个系统了。"""
    engine = DecisionEngine()
    acts = engine.decide(_det(neutered=EventNeutered(value=False, confidence=0.5)))
    assert _acts(acts, "TNR_TASK_CREATED") == []


def test_no_tnr_when_unknown() -> None:
    engine = DecisionEngine()
    acts = engine.decide(_det(neutered=EventNeutered(value=None, confidence=None)))
    assert _acts(acts, "TNR_TASK_CREATED") == []


# --- 总线 / 存储 -------------------------------------------------------------


def test_bus_records_by_type(tmp_path) -> None:
    bus = EventBus()
    jl = tmp_path / "events.jsonl"
    bus.to_jsonl(jl)
    bus.publish(sample_detection_event())
    bus.publish(sample_detection_event(**{"event_id": "det-x"}))
    bus.close()
    assert len(bus.detections) == 2
    assert len(jl.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_store_roundtrip() -> None:
    from tests.factories import sample_action_event

    s = Store(":memory:")
    ev = sample_action_event(status="queued")
    s.record_action(ev)
    s.record_detection(sample_detection_event())
    assert s.last_feed_at("cat-001") is not None
    assert s.counts()["action_events"] == 1
