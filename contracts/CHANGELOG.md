# 契约变更记录

格式：`日期 · 版本 · 改动 · 原因 · 影响`

破坏性变更必须升版本目录（`v1` → `v2`），并在此说明迁移方式。

---

## v1.0 — 冻结

- 建立 5 个契约：`FramePacket` / `CatFace` / `EarNotch` / `DetectionEvent` / `ActionEvent`
- 关键约定：
  - 帧只传路径（`image_path`），不传 base64
  - `CatFace.landmarks` 固定 7 点，耳尖可为 `null`
  - `EarNotch`：`visible=false` ⇒ `notched=null`（JSON Schema 强制）
  - 对外只发聚合后的 `DetectionEvent`，不暴露单帧结果
  - `DetectionEvent.evidence.concurrent_tracks` 用于「多猫不投粮」判断
- 影响：全体
