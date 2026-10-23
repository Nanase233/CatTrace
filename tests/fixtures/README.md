# 测试素材

放**很小**的样本，让猫脸、耳标模块不用摄像头也能写单测。

规则：
- 单文件 < 2MB，整个目录 < 10MB。大素材走 `datasets/`（已在 .gitignore 里，不入 Git）。
- 命名说清用途：`cat_face_front_640x480.jpg`、`ear_notch_left_visible.jpg`。
- 二进制用了 Git LFS 之外的方式就别再加了；要加先跟大家说一声。

## 现在这里应该有什么

| 文件 | 用途 | 谁用 |
|---|---|---|
| `frame_640x480.jpg` | 最小合法 FramePacket 的图片 | 三个模块 |
| `cat_front_v1.jpg` | 正面猫脸，7 个关键点都可见 | 猫脸、耳标模块 |
| `cat_side_v1.jpg` | 侧脸，一只耳尖不可见 | 耳标模块（测 `visible=false`） |
| `ear_notched_left_v1.jpg` | 左耳剪口清晰 | 耳标模块 |
| `ear_intact_v1.jpg` | 两只耳朵都完整 | 耳标模块 |

## 没素材怎么办

```bash
python scripts/record_frames.py --source csi://0 --fps 2 --seconds 60 --out datasets/raw/2026-10-22
python scripts/record_frames.py --source synthetic:1 --out tests/fixtures   # 造一张占位图
```

`file:` 源可以直接吃目录，所以把录下来的帧丢给 `--source file:datasets/raw/2026-10-22/frames`
就能在没有摄像头的机器上跑完整流水线。
