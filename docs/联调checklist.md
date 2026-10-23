# 联调 Checklist

> 每次要「三个模块一起跑一次」之前，按这个表过一遍。
> 目的：把「谁卡谁」变成一张能打勾的表，而不是群里互相等。

## 0. 每次开跑前（5 分钟）

- [ ] 三个模块都在 `dev` 的最新提交上（`git pull && git log -1`）
- [ ] `pytest -q` 全绿
- [ ] `python -m pipeline.runner --source synthetic:30 --mock-all` 打印 `PIPELINE OK`
- [ ] 没人有未提交的 `contracts/` 改动
- [ ] 需要用的素材已经在 `datasets/raw/<日期>/frames` 里

## 1. 单人自检（各自做完就做，不要攒着）

### 猫脸识别

- [ ] `analyze()` 能接 `FramePacket`、返回 `list[CatFace]`
- [ ] 输出过得了 `validate("cat_face", face)`
- [ ] 7 个关键点键齐全，耳尖不可见时给 `null`
- [ ] 同一只猫连续帧 `track_id` 稳定
- [ ] 空画面返回 `[]` 不抛异常
- [ ] 说得出自己的推理耗时（Pi4 上目标 < 350ms/帧）

### 耳标识别

- [ ] `analyze(packet, faces)` 返回长度与 `faces` 一致，`track_id` 对得上
- [ ] 输出过得了 `validate("ear_notch", ear)`
- [ ] `visible=false` 时 `notched` / `score` 都是 `null`
- [ ] 水平翻转增强有交换左右标签的单测
- [ ] 说得出自己的推理耗时（目标 < 150ms/帧）

### 摄像头与联调

- [ ] `csi://0` 能出帧，`/dev/shm/catvision/frames` 有文件
- [ ] `file:` / `synthetic:` 回放源正常（这是另外两个模块不接硬件的前提）
- [ ] 帧目录不会无限涨（`--keep-frames` 生效）
- [ ] `vcgencmd get_throttled` == `0x0`（非 0 = 供电不足，必须先解决）
- [ ] 端到端 fps 报得出来

## 2. 两个模块对接（猫脸 × 耳标）

- [ ] 用**同一个** `packet` 跑：猫脸模块的输出直接喂给耳标模块
- [ ] 耳标模块裁出的耳部 ROI 是**耳朵**，不是整张脸或脖子（把 ROI 存图人眼看一遍）
- [ ] 侧脸 / 一只耳不可见的样本上，耳标模块老实给 `visible=false`
- [ ] 猫脸模块的 `head_pose.yaw` 大角度时，耳标模块的判定不崩

```bash
python -m pipeline.runner --source file:datasets/raw/joint/frames \
    --catface modules.catface:M1CatFaceModule \
    --earnotch modules.earnotch:EarNotchModel \
    --jsonl /tmp/joint.jsonl
```

## 3. 三个模块合练（真链路）

- [ ] `--source csi://0` 跑 60 帧，无异常退出
- [ ] 事件流里有 `DetectionEvent`，`evidence.frames_seen` 合理（不是 1）
- [ ] 识别对的猫 → `FEED_DISPENSE`，且 `payload.dry_run=true`
- [ ] 多猫同框 → **没有** `FEED_DISPENSE`（重点验这条）
- [ ] 未剪耳 → 有 `TNR_TASK_CREATED`
- [ ] 已剪耳 → **没有** `TNR_TASK_CREATED`
- [ ] 同一只猫 10 秒内不重复触发
- [ ] 断开摄像头再插上，进程不崩（或至少日志里有明确报错）

## 4. 性能基线（Pi4 · 1GB）

| 环节 | 预算 | 实测 |
|---|---|---|
| 采集 + 落盘 | < 40ms | |
| 猫脸检测 + 识别 + 关键点 | < 350ms | |
| 剪耳判定 | < 150ms | |
| 聚合 + 决策 | < 10ms | |
| **端到端 / 帧** | **< 550ms（≥ 2fps）** | |

- [ ] `free -m` 剩余内存 > 150MB（低于这个数就要怀疑内存泄漏）
- [ ] 连续跑 30 分钟，`seq` 没有大跳（丢帧率 < 5%）

## 5. 出问题时按这个顺序查

1. **契约不通** → `pytest tests/contract -q`，看 schema 和 pydantic 哪边不一致
2. **拿不到帧** → `python -m modules.camera --source csi://0 --frames 3 -v`
3. **猫脸模块没输出** → 单独喂一张固定图，排除是不是输入问题
4. **耳标模块的输出对不上猫脸模块** → 打印两边 `track_id` 列表比对
5. **该投粮没投** → 看日志里的 `跳过投粮：<原因>`，四种原因分别对应契约里的四道闸
6. **不该投粮却投了** → 看 `votes` 和 `concurrent_tracks`，先怀疑聚合层
