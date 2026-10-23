# 接口契约 v1（唯一权威来源）

**任何跨模块的数据都必须符合这里的定义。** 字段名就是代码里的字段名，不要自己改名。

- 机器可读规范：`contracts/v1/*.schema.json`（JSON Schema draft 2020-12）
- Python 绑定：`contracts/python/catvision_contracts/models.py`（pydantic v2）
- 模块接口：`contracts/python/catvision_contracts/interfaces.py`（Protocol）
- 变更记录：`contracts/CHANGELOG.md`

---

## 1. FramePacket —— 摄像头模块 → 猫脸模块 / 耳标模块

```json
{
  "schema": "catvision.frame_packet/1.0",
  "packet_id": "cam0-20261022T083012.345-000123",
  "camera_id": "cam0",
  "captured_at": "2026-10-22T08:30:12.345+08:00",
  "seq": 123,
  "width": 640,
  "height": 480,
  "format": "jpeg",
  "image_path": "/dev/shm/catvision/frames/000123.jpg",
  "image_sha1": "3f2a...",
  "source": { "kind": "csi", "uri": "csi://0" }
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema` | string | ✅ | 固定 `catvision.frame_packet/1.0` |
| `packet_id` | string | ✅ | 全局唯一，后续结果都带它，用于串联 |
| `camera_id` | string | ✅ | 摄像头标识 |
| `captured_at` | string(date-time) | ✅ | 带时区 |
| `seq` | int ≥0 | ✅ | 单调递增帧号 |
| `width` / `height` | int ≥1 | ✅ | 图像尺寸 |
| `format` | enum | ✅ | `jpeg` / `png` |
| `image_path` | string | ✅ | **图片路径，不塞 base64**；Pi 上写 `/dev/shm` 内存盘 |
| `image_sha1` | string\|null | | 校验用 |
| `source.kind` | enum | ✅ | `csi` / `usb` / `rtsp` / `file` / `synthetic` |

---

## 2. CatFace —— 猫脸模块 → 耳标模块 / 决策层

```json
{
  "schema": "catvision.cat_face/1.0",
  "packet_id": "cam0-20261022T083012.345-000123",
  "track_id": "t-0007",
  "bbox": [210, 96, 148, 152],
  "det_score": 0.94,
  "landmarks": {
    "left_eye": [248, 168], "right_eye": [322, 166], "nose": [286, 205],
    "left_ear_base": [232, 118], "right_ear_base": [340, 116],
    "left_ear_tip": [214, 78], "right_ear_tip": [358, 76]
  },
  "head_pose": { "yaw": -12.5, "pitch": 4.0, "roll": 2.1 },
  "identity": {
    "cat_id": "cat_0001", "name": "大橘", "similarity": 0.86,
    "decision": "matched", "gallery_version": "g2026-10-20"
  },
  "quality": { "blur": 118.4, "brightness": 132.0, "is_usable": true }
}
```

| 字段 | 说明 |
|---|---|
| `bbox` | `[x, y, w, h]` 像素，**左上角 + 宽高**，基于 FramePacket 尺寸 |
| `track_id` | 个体追踪 ID，同段视频内保持一致（猫脸模块维护） |
| `landmarks` | 7 点：双眼 / 鼻 / 双耳根 / 双耳尖。**耳尖可为 null**（不可见时）。耳标模块强依赖 |
| `head_pose` | 偏航 yaw / 俯仰 pitch / 滚转 roll（度）。耳标模块用它做可见性门控 |
| `identity.decision` | `matched` / `unknown` / `ambiguous` |
| `quality` | 质量分，用于挑最佳帧建档 |

> ⚠️ **识别是开集问题**：必须允许说「我不认识」。`ambiguous` 表示相似度落在不确定区间，决策层会按保守策略处理（不投粮）。

---

## 3. EarNotch —— 耳标模块 → 决策层

```json
{
  "schema": "catvision.ear_notch/1.0",
  "packet_id": "cam0-20261022T083012.345-000123",
  "track_id": "t-0007",
  "left":  { "visible": true,  "notched": true, "score": 0.88, "bbox": [206, 66, 62, 70] },
  "right": { "visible": false, "notched": null, "score": null, "bbox": null },
  "neutered": { "value": true, "source": "ear_notch", "confidence": 0.88, "rule": "any_ear_notched" },
  "model_version": "earnotch-v0.3.1"
}
```

**语义约定（已写进 JSON Schema，违反会校验失败）**

- `visible=false` → `notched` 必须是 `null`。**看不见就说看不见，禁止猜。**
- **剪耳（ear tip）= 已完成绝育 / TNR**；未剪耳 = 疑似未绝育。
- `neutered.rule` 默认 `any_ear_notched`（任一侧剪耳即认为绝育），是**配置项**不是模型输出。
- 误判代价不对称：宁可输出 `uncertain`，也不要高置信度判错。

---

## 4. DetectionEvent —— 决策层 → 前端（聚合后）

```json
{
  "schema": "catvision.detection_event/1.0",
  "event_id": "evt-9f3c...",
  "emitted_at": "2026-10-22T08:30:15.120+08:00",
  "camera_id": "cam0",
  "track_id": "t-0007",
  "cat": { "cat_id": "cat_0001", "name": "大橘", "similarity": 0.86, "decision": "matched" },
  "neutered": { "value": true, "confidence": 0.88 },
  "votes": { "identity": { "cat_0001": 6, "unknown": 1 }, "ear": { "notched": 5, "clean": 2 } },
  "evidence": {
    "frames_seen": 7,
    "concurrent_tracks": 1,
    "first_seen": "2026-10-22T08:30:12.345+08:00",
    "last_seen": "2026-10-22T08:30:15.010+08:00",
    "best_frame_path": "/dev/shm/catvision/best/t-0007.jpg",
    "snapshot_url": null
  }
}
```

单帧结果噪声太大，**对外只发聚合后的事件**（同一 `track_id` 投票 N 帧后）。
`evidence.concurrent_tracks` 表示同一时刻画面里的猫数量，决策引擎用它做「多猫不投粮」判断。

---

## 5. ActionEvent —— 投粮 / TNR / 告警

```json
{
  "schema": "catvision.action_event/1.0",
  "event_id": "act-77ab...",
  "emitted_at": "2026-10-22T08:30:15.200+08:00",
  "type": "FEED_DISPENSE",
  "track_id": "t-0007",
  "cat_id": "cat_0001",
  "reason": "identity_confirmed_and_cooldown_passed",
  "payload": { "portion_ms": 800, "cooldown_until": "2026-10-22T14:30:15+08:00" },
  "status": "queued"
}
```

- `type`：`FEED_DISPENSE` / `TNR_TASK_CREATED` / `ALERT`
- `status`：`queued` / `executed` / `failed` / `skipped`

---

## 6. 模块接口（Python Protocol）

```python
class CatFaceModule(Protocol):
    def analyze(self, packet: FramePacket) -> list[CatFace]: ...

class EarNotchModule(Protocol):
    def analyze(self, packet: FramePacket, faces: list[CatFace]) -> list[EarNotch]: ...
```

猫脸和耳标模块只要实现这两个方法就能接进主流水线，**不需要改 `pipeline/` 里任何代码**。
