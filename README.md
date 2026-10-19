# 🐱 CatTrace

> **"看见每一只猫，守护每一个家。"**
>
> 基于 AIoT 的流浪猫科学救助平台

---

## 三大核心功能

| 功能 | 说明 |
|------|------|
| 📹 **实时直播** | 模拟猫咪直播间，实时环境监测 |
| 🍖 **远程投喂** | 一键投喂，记录透明可追溯 |
| 📋 **猫咪档案** | AI 建档，健康状态与互动数据一目了然 |

---

## 快速开始

### Flask 完整版

```bash
pip install -r requirements.txt
python app.py
# 浏览器打开 http://localhost:5000
```

### 静态演示页（零依赖）

双击打开 `demo.html`，无需 Python、无需网络。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.6+ · Flask |
| 前端 | HTML5 + CSS3 + JavaScript（原生，零框架） |
| 数据 | JSON 文件存储（零数据库依赖） |
| 智能 | 自学习引擎（纯 Python 标准库实现） |
| PWA | Service Worker · Web App Manifest |

## 项目结构

```
CatTrace/
├── app.py                # Flask 后端服务器（REST API + 自学习集成）
├── self_learning.py      # 自学习引擎（行为分析 / 异常检测 / 健康评分）
├── demo.html             # 独立静态演示页（双击即开）
├── requirements.txt      # Python 依赖
├── 项目说明书.md          # 详细项目说明书
├── templates/            # Flask 前端模板
│   ├── index.html        # 首页（实时直播）
│   ├── cats.html         # 猫咪档案页
│   ├── diary.html        # 猫咪日记页
│   └── adopt.html        # 领养中心页
└── static/               # 静态资源
    ├── manifest.json      # PWA 应用清单
    ├── sw.js              # Service Worker
    ├── css/style.css      # 全局样式（含深色模式）
    └── js/main.js         # 前端交互逻辑
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（实时直播） |
| `/cats` | GET | 猫咪档案页 |
| `/diary` | GET | 猫咪日记页 |
| `/adopt` | GET | 领养中心页 |
| `/api/cats` | GET | 获取所有猫咪列表 |
| `/api/cat/<id>` | GET | 获取单个猫咪详情 |
| `/api/stats` | GET | 获取统计数据 |
| `/api/feed` | POST | 投喂猫咪 |
| `/api/feed-logs` | GET | 获取投喂记录 |
| `/api/adopt/apply` | POST | 提交领养申请 |
| `/api/learning/*` | GET/POST | 自学习引擎接口（8 个） |

---

**CatTrace 项目组** · GitHub: [chenglian07/mao](https://github.com/chenglian07/mao)