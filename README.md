# CatTrace

> 看见每一只猫，守护每一个家。
>
> 基于 AIoT 的流浪猫科学救助与社区共治平台 MVP

---

## 三大核心功能

| # | 功能 | 等级 | 状态 |
|---|------|------|------|
| 1 | 实时直播与在线巡检 | P0 | MVP 模拟 |
| 2 | 远程投喂与投喂追溯 | P0 | 已完成 |
| 3 | AI 猫咪档案 | P0 | 已完成 |

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

---

CatTrace 项目组 -- [chenglian07/mao](https://github.com/chenglian07/mao)