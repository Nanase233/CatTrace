# CatTrace REST API 接口文档

> 所有接口基于 Flask，返回 JSON 格式。基础地址：`http://localhost:5000`

---

## 页面路由

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页（实时直播与在线巡检） |
| `/cats` | GET | 猫咪档案页 |
| `/diary` | GET | 猫咪日记页 |
| `/adopt` | GET | 领养中心页 |

## 核心数据接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/cats` | GET | 获取所有猫咪 |
| `/api/cat/<id>` | GET | 单只猫咪详情 |
| `/api/stats` | GET | 统计数据 |
| `/api/feed` | POST | 投喂猫咪 |
| `/api/feed-logs` | GET | 投喂记录 |
| `/api/stats/feed-history` | GET | 投喂历史 |
| `/api/export` | GET | 导出全量数据 |

## 业务功能接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/diary/entries` | GET | 猫咪日记列表 |
| `/api/diary/<id>/like` | POST | 给日记点赞 |
| `/api/diary/<id>/comment` | POST | 给日记评论 |
| `/api/adopt/apply` | POST | 提交领养申请 |
| `/api/report` | POST | 提交举报 |
| `/api/reports` | GET | 举报列表 |
| `/api/volunteer/apply` | POST | 申请志愿者 |
| `/api/volunteers` | GET | 志愿者列表 |
| `/api/emergency/alerts` | GET | 紧急求助列表 |
| `/api/location/<cat_id>` | GET | 猫咪位置（按权限脱敏） |
| `/api/notifications` | GET | 通知列表 |

## 认证接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/auth/login` | POST | 登录（MVP 验证码：8888） |
| `/api/auth/register` | POST | 注册 |
| `/api/auth/profile` | GET | 当前用户信息 |
| `/api/auth/logout` | POST | 退出登录 |

## 财务接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/finance/summary` | GET | 财务概览 |
| `/api/finance/transactions` | GET | 交易记录 |
| `/api/finance/monthly` | GET | 月度趋势 |

## 自学习接口

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/learning/cat-profile/<id>` | GET | 猫咪学习画像 |
| `/api/learning/user-profile/<user_id>` | GET | 用户偏好画像 |
| `/api/learning/recommendations/<user_id>` | GET | 个性化推荐 |
| `/api/learning/anomalies` | GET | 异常预警列表 |
| `/api/learning/insights` | GET | 全局模式洞察 |
| `/api/learning/health-report/<id>` | GET | 猫咪健康报告 |
| `/api/learning/feedback` | POST | 提交识别纠错 |
| `/api/learning/train` | POST | 触发模型重训练 |