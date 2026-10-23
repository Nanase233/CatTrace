"""投票聚合：把逐帧结果合成对外事件。

为什么要聚合：
- 单帧结果不稳定（一帧剪耳判定错就会误触发投粮 / 误建 TNR 任务）
- 对外只发 DetectionEvent，前端不用自己写投票逻辑
- 顺手算 concurrent_tracks：多猫同框时不投粮（防止一只猫吃光）
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from catvision_contracts import (
    CatFace,
    DetectionEvent,
    EarNotch,
    EventCat,
    EventNeutered,
    Evidence,
    FramePacket,
    Votes,
    new_id,
)

# 跟踪连续多少秒没出现，就认为这只猫走了，可以出事件了
DEFAULT_TRACK_TIMEOUT = 3.0
# 同一 track 至少看到几帧才允许出事件（防抖）
DEFAULT_MIN_FRAMES = 1
# 同一 camera 的时间分桶宽度（秒）：用于统计 concurrent_tracks
CONCURRENCY_WINDOW = 1.0
# 个体识别要「认定是某只猫」，得票率必须高于这个值，否则算 ambiguous。
# 3:3 平票 → 0.5 → ambiguous；8:1 → 0.89 → matched
MAJORITY_THRESHOLD = 0.6


class _TrackState:
    __slots__ = (
        "track_id", "camera_id", "identity_votes", "ear_votes", "frames_seen",
        "first_seen", "last_seen", "best_frame_path", "best_score",
        "similarity_sum", "similarity_n", "neutered_true", "neutered_false",
        "neutered_conf_sum", "neutered_conf_n", "gallery_version", "name",
    )

    def __init__(self, track_id: str, camera_id: str, now: datetime) -> None:
        self.track_id = track_id
        self.camera_id = camera_id
        self.identity_votes: Counter = Counter()
        self.ear_votes: Counter = Counter()
        self.frames_seen = 0
        self.first_seen = now
        self.last_seen = now
        self.best_frame_path: str | None = None
        self.best_score = -1.0
        self.similarity_sum = 0.0
        self.similarity_n = 0
        self.neutered_true = 0
        self.neutered_false = 0
        self.neutered_conf_sum = 0.0
        self.neutered_conf_n = 0
        self.gallery_version = "unknown"
        self.name: str | None = None


class TrackAggregator:
    """按 (camera_id, track_id) 累积逐帧结果。"""

    def __init__(
        self,
        *,
        track_timeout: float = DEFAULT_TRACK_TIMEOUT,
        min_frames: int = DEFAULT_MIN_FRAMES,
    ) -> None:
        self.track_timeout = track_timeout
        self.min_frames = min_frames
        self._tracks: dict[tuple[str, str], _TrackState] = {}
        self._concurrency: dict[str, list[tuple[float, str]]] = defaultdict(list)

    # -- 输入 -------------------------------------------------------------
    def update(
        self,
        packet: FramePacket,
        faces: list[CatFace],
        ears: list[EarNotch],
        *,
        observed_at: datetime | None = None,
    ) -> None:
        now = observed_at or packet.captured_at
        self._note_concurrency(packet, faces, now)

        ear_by_track = {e.track_id: e for e in ears}
        for face in faces:
            if not face.quality.is_usable:
                continue  # 质量太差的帧不参与投票
            st = self._state(packet.camera_id, face.track_id, now)
            st.frames_seen += 1
            st.last_seen = now
            st.gallery_version = face.identity.gallery_version

            if face.identity.decision == "matched" and face.identity.cat_id:
                st.identity_votes[face.identity.cat_id] += 1
                if face.identity.name:
                    st.name = face.identity.name
            else:
                st.identity_votes["__unknown__"] += 1
            if face.identity.similarity is not None:
                st.similarity_sum += face.identity.similarity
                st.similarity_n += 1

            # 最佳帧：检测分 + 清晰度综合
            score = face.det_score * (face.quality.blur / 200.0 if face.quality.blur else 1.0)
            if score > st.best_score:
                st.best_score = score
                st.best_frame_path = packet.image_path

            ear = ear_by_track.get(face.track_id)
            if ear is not None and ear.neutered.value is not None:
                st.ear_votes["neutered" if ear.neutered.value else "intact"] += 1
                if ear.neutered.value:
                    st.neutered_true += 1
                else:
                    st.neutered_false += 1
                if ear.neutered.confidence is not None:
                    st.neutered_conf_sum += ear.neutered.confidence
                    st.neutered_conf_n += 1
            else:
                st.ear_votes["unknown"] += 1

    def _state(self, camera_id: str, track_id: str, now: datetime) -> _TrackState:
        key = (camera_id, track_id)
        if key not in self._tracks:
            self._tracks[key] = _TrackState(track_id, camera_id, now)
        return self._tracks[key]

    def _note_concurrency(self, packet: FramePacket, faces: list[CatFace], now: datetime) -> None:
        ts = now.timestamp()
        bucket = self._concurrency[packet.camera_id]
        for f in faces:
            bucket.append((ts, f.track_id))

    def concurrent_tracks(self, camera_id: str, at: datetime | float) -> int:
        """统计 at 时刻前后 CONCURRENCY_WINDOW 秒内出现过的不重复 track 数。"""
        ts = at.timestamp() if isinstance(at, datetime) else at
        seen = {
            tid
            for (t, tid) in self._concurrency.get(camera_id, [])
            if abs(t - ts) <= CONCURRENCY_WINDOW
        }
        return max(len(seen), 1)

    # -- 输出 -------------------------------------------------------------
    def flush_track(self, camera_id: str, track_id: str) -> DetectionEvent | None:
        st = self._tracks.pop((camera_id, track_id), None)
        if st is None or st.frames_seen < self.min_frames:
            return None
        return self._build_event(st)

    def flush_stale(self, now: datetime | None = None) -> list[DetectionEvent]:
        now = now or datetime.now(timezone.utc)
        stale = [
            key
            for key, st in self._tracks.items()
            if (now - st.last_seen).total_seconds() >= self.track_timeout
        ]
        events = []
        for cam, tid in stale:
            ev = self.flush_track(cam, tid)
            if ev:
                events.append(ev)
        return events

    def flush_all(self) -> list[DetectionEvent]:
        events = []
        for cam, tid in list(self._tracks.keys()):
            ev = self.flush_track(cam, tid)
            if ev:
                events.append(ev)
        return events

    def _build_event(self, st: _TrackState) -> DetectionEvent:
        identity_votes = dict(st.identity_votes)
        ear_votes = dict(st.ear_votes)

        real = {k: v for k, v in identity_votes.items() if k != "__unknown__"}
        if real:
            cat_id, votes = max(real.items(), key=lambda kv: kv[1])
            total = sum(identity_votes.values())
            if votes / total < MAJORITY_THRESHOLD:
                # 票数不够集中：宁可说 ambiguous，也不要把粮投给错的猫
                decision, cat_id = "ambiguous", None
            else:
                decision = "matched"
        else:
            cat_id, decision = None, "unknown"

        sim = round(st.similarity_sum / st.similarity_n, 3) if st.similarity_n else None

        if st.neutered_true and st.neutered_false:
            # 左右判矛盾的帧都有：取多数；完全平手就不下结论
            if st.neutered_true > st.neutered_false:
                value = True
            elif st.neutered_false > st.neutered_true:
                value = False
            else:
                value = None
        elif st.neutered_true:
            value = True
        elif st.neutered_false:
            value = False
        else:
            value = None

        conf = (
            round(st.neutered_conf_sum / st.neutered_conf_n, 3) if st.neutered_conf_n else None
        )

        return DetectionEvent(
            event_id=new_id("det"),
            emitted_at=datetime.now(timezone.utc),
            camera_id=st.camera_id,
            track_id=st.track_id,
            cat=EventCat(cat_id=cat_id, name=st.name, similarity=sim, decision=decision),
            neutered=EventNeutered(value=value, confidence=conf),
            votes=Votes(identity=identity_votes, ear=ear_votes),
            evidence=Evidence(
                frames_seen=st.frames_seen,
                concurrent_tracks=self.concurrent_tracks(st.camera_id, st.last_seen),
                first_seen=st.first_seen,
                last_seen=st.last_seen,
                best_frame_path=st.best_frame_path,
            ),
        )

    @property
    def active_tracks(self) -> int:
        return len(self._tracks)
