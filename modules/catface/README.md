# 猫脸识别模块

> 你的输入是 `FramePacket`，输出是 `list[CatFace]`。除此之外的一切都不用管。

## 1. 你要实现的就一个方法

```python
from catvision_contracts import CatFace, FramePacket

class M1CatFaceModule:
    def analyze(self, packet: FramePacket) -> list[CatFace]:
        ...
```

签名写死在 `contracts/python/catvision_contracts/interfaces.py` 的 `CatFaceModule` 协议里。
流水线只会这样调你，别加别的必填参数（可选参数给默认值就行）。

## 2. 拿到一帧长什么样

```json
{
  "schema": "catvision.frame_packet/1.0",
  "packet_id": "cam0-20261022T101500.123-000042",
  "camera_id": "cam0",
  "captured_at": "2026-10-22T10:15:00.123Z",
  "seq": 42,
  "width": 640,
  "height": 480,
  "format": "jpeg",
  "image_path": "/dev/shm/catvision/frames/cam0/f000042.jpg",
  "image_sha1": "…",
  "source": { "kind": "csi", "uri": "csi://0" }
}
```

**图在 `image_path` 指向的文件里**，不在内存里传。读法：

```python
from PIL import Image
img = Image.open(packet.image_path)
```

为什么这么设计：帧可能在另一个进程，也可能被 ffmpeg 抽出来。走文件是最省事、最不可能踩坑的。

## 3. 你必须回什么东西

看 `contracts/v1/cat_face.schema.json`。最容易踩的三点：

### (1) 7 个关键点，一个都不能少

| 键 | 含义 |
|---|---|
| `left_eye` / `right_eye` | 双眼 |
| `nose` | 鼻头 |
| `left_ear_base` / `right_ear_base` | **耳根**（耳廓与头连接处） |
| `left_ear_tip` / `right_ear_tip` | **耳尖** |

坐标是相对 `packet.width/height` 的像素坐标 `[x, y]`。

**耳尖看不见就给 `null`，不要瞎填坐标。** 耳标模块的耳部 ROI 完全靠 `ear_base` 和 `ear_tip`
这两个点去裁，你填错或省略，耳标模块那边直接崩。这一点是两个模块能不能合上的分水岭。

> 左右是**猫的左右**，不是画面的左右。猫正对你时，它的左耳在画面右侧。
> 这一点写单测锁住。

### (2) `track_id` 在同一段视频里对同一只猫必须一致

耳标模块用它把剪耳结果对回猫，聚合层用它做投票。你每帧换新 id = 投票永远得不出结论。

### (3) 不认识就说 `unknown`，不要强行匹配最近邻

`identity.decision` 三选一：`matched` / `unknown` / `ambiguous`。
乱报 `matched` 的后果是**给错的猫投粮**——这是整个项目最贵的 bug。
判不准就给 `unknown`，或把 `similarity` 老实报低。

## 4. 怎么在没有摄像头的情况下开发

```bash
# 你的输入：合成源造的图，或者你们录下来的图
python -m modules.camera --source synthetic:5                  # 交互式看一帧
python scripts/record_frames.py --source csi://0 --fps 2 --seconds 60 --out datasets/raw/mine

# 自己单独调你的模块（不用管耳标模块和摄像头模块）
python - <<'PY'
from modules.camera.capture import CameraStream
from modules.catface import M1CatFaceModule
with CameraStream("file:datasets/raw/mine/frames", fps=1) as cam:
    for packet in cam.packets(max_frames=3):
        for face in M1CatFaceModule().analyze(packet):
            print(face.to_json())
PY

# 接进完整链路（耳标模块还没做完，先用它的 Mock）
python -m pipeline.runner --source file:datasets/raw/mine/frames \
    --catface modules.catface:M1CatFaceModule --earnotch mocks:MockEarNotchModule
```

**随时可以自测：** 只要你的输出能通过下面的校验，接进去就不会炸。

```bash
pytest tests/contract -q                    # 契约没被你改坏
python -c "
from catvision_contracts import validate
from modules.catface import M1CatFaceModule
from modules.camera.capture import CameraStream
with CameraStream('synthetic:1', fps=1) as cam:
    for p in cam.packets(max_frames=1):
        for f in M1CatFaceModule().analyze(p):
            validate('cat_face', f); print('契约 OK', f.track_id)
"
```

## 5. 你的提交里要有测试

最少这几个，缺一个评审就会打回：

- [ ] 关键点顺序/左右正确性（建议用一张正脸图固定期望值）
- [ ] **水平翻转增强时，左右关键点标签和左右耳标签同步交换**（最容易出静默 bug 的地方）
- [ ] 空画面 → 返回 `[]`，不能抛异常
- [ ] 同一只猫连续几帧 → `track_id` 保持不变
- [ ] 输出能过 `validate("cat_face", face)`

## 6. 分支 / 提交

```
feat/catface-<简述>        # 从 dev 切
earnotch: xxx              # 不是你的活别改
catface: 加入 7 点关键点回归测试
```

改 `contracts/` 要单独开 `contract:` PR，并且另外两个模块 approve。
