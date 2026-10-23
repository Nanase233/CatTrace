# CatTrace

> 看见每一只猫，守护每一个家。
>
> 基于 AIoT 的流浪猫科学救助与社区共治平台 MVP

---

## 三大核心功能

| # | 功能 | 等级 | 说明 |
|---|------|------|------|
| 1 | 实时直播与在线巡检 | P0 | 树莓派/香橙派边缘节点推流，远程查看猫咪状态 |
| 2 | 远程投喂与投喂追溯 | P0 | 一键投喂，全链路记录，数据透明可追溯 |
| 3 | AI 猫咪档案 | P0 | 每只猫的数字身份：基本信息、健康、绝育、互动数据 |

自学习引擎（`self_learning.py`）作为贯穿三大功能的 AI 能力层，提供投喂规律学习、异常检测、健康评分等能力。详见 [docs/self-learning.md](./docs/self-learning.md)。

## 快速开始

### Flask 完整版（推荐）

```bash
python --version   # 需要 3.6+
pip install -r requirements.txt
python app.py
# 浏览器打开 http://localhost:5000
```

页面路由：`/`（首页直播）、`/cats`（猫咪档案）、`/diary`（日记）、`/adopt`（领养中心）。

### 静态演示页（零依赖）

双击打开 `demo.html`，无需 Python、无需网络。详见 [docs/demo-guide.md](./docs/demo-guide.md)。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/user-guide.md](./docs/user-guide.md) | 用户说明书（面向评审教师与使用者） |
| [docs/api.md](./docs/api.md) | REST API 完整接口文档 |
| [docs/self-learning.md](./docs/self-learning.md) | 自学习模块：目标、边界、数据闭环、评价指标 |
| [docs/roadmap.md](./docs/roadmap.md) | P0-P3 路线图与远期规划 |
| [docs/business-plan.md](./docs/business-plan.md) | 市场分析、技术方案、产品范围 |
| [docs/demo-guide.md](./docs/demo-guide.md) | demo.html 静态演示页使用说明 |
| [docs/验证指南.md](./docs/验证指南.md) | ⭐ 怎么证明摄像头接入 + 模块联调真的实现（五层验证 + 自证脚本） |

---

## 协作者代码

`collaborators/` 目录保留了各协作者的原始代码和文档，未经修改：

| 目录 | 内容 |
|------|------|
| collaborators/mao-main | 主项目原始版本（含 MeowGuard 时期文档） |
| collaborators/项目猫-MVP | MVP 原型版本（含猫脸识别等实验功能） |

---

## 树莓派 AI 识别模块（CatVision）

树莓派 4B 上的猫脸识别 + 剪耳识别原型代码已并入本仓库根目录，与 Flask 网页共用同一个仓库：

| 目录 | 内容 |
|------|------|
| `contracts/` | ⭐ 接口契约（JSON Schema + pydantic 绑定），三个模块共管 |
| `modules/camera/` | 摄像头接入：CSI / USB / RTSP / 文件回放 / 合成源 |
| `modules/catface/` | 猫脸识别（个体 ID + 关键点），待实现 |
| `modules/earnotch/` | 剪耳（绝育）识别，待实现 |
| `pipeline/` | 抽帧 → 识别 → 投票聚合 → 决策（投粮 / TNR）→ 事件总线 |
| `mocks/` | 各模块 Mock，保证各模块能并行开发 |
| `tests/` | 契约测试 + 全链路单测 |

接手分工与目录说明见 [README-catvision.md](./README-catvision.md)，
字段级接口见 [docs/接口规范.md](./docs/接口规范.md)。

没有摄像头也能跑通全链路：

```bash
pip install -e ".[dev]"
pytest -q
python -m pipeline.runner --source synthetic:60 --mock-all   # 看到 PIPELINE OK 即通过
```

一条命令自证「摄像头接入 + 模块联调」是否真的打通（五层验证，逐项 PASS/FAIL）：

```bash
python scripts/verify_catvision.py
```

没有摄像头的开发机 L1~L4 全绿、L5 自动 `[SKIP]`；树莓派插着 CSI 摄像头时 L1~L5 全绿。
判据、反造假检查表、本轮实测记录见 [docs/验证指南.md](./docs/验证指南.md)。

---

CatTrace 项目组 -- [chenglian07/mao](https://github.com/chenglian07/mao)