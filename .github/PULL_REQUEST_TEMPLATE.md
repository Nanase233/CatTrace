## 这个 PR 做什么

<!-- 一句话说明这个 PR 的目的；关联 issue 写 Closes #123 -->

## 类型

- [ ] feat：新功能
- [ ] fix：修 bug
- [ ] docs：文档
- [ ] test：测试
- [ ] refactor：重构（不改变行为）
- [ ] chore：构建 / 依赖 / 杂项

## 影响范围（勾选实际碰到的目录）

- [ ] `modules/camera/` · `pipeline/` · `scripts/` · `deploy/`
- [ ] `modules/catface/`
- [ ] `modules/earnotch/`
- [ ] `contracts/`（**必须同时更新 `contracts/CHANGELOG.md`，并由另外两个模块 owner approve**）
- [ ] Web 端（`app.py` · `templates/` · `static/` · `live_proxy.py` · `self_learning.py`）
- [ ] 文档（`README*.md` · `docs/`）

## 提交前自检（对应 `docs/接手流程.md` 第五节）

- [ ] `pytest -q` 通过
- [ ] `python scripts/verify_catvision.py` 通过（没插摄像头时 L5 显示 `[SKIP]` 属正常）
- [ ] `ruff check .` 通过
- [ ] 跨模块只通过 `contracts/` 交互，没有 import 别人模块的内部实现
- [ ] 新增的模块或行为带了 Mock（没有 Mock 就没有并行）

> 三条命令全过再提 PR，CI 基本一次就绿。

## 给 reviewer 的导读

<!-- 关键设计取舍是什么、建议先看哪几个文件、哪一块最需要重点看 -->

## 实测输出 / 截图（链路或 UI 改动必填）

```text
粘贴 PIPELINE OK、接口返回、页面截图（拖进来）等
```

## 目标分支

按 `docs/接手流程.md` 第四节：分支 → 评审分支，**不要直接推 `main`**。
