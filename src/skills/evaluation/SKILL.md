# Evaluation

你能判断项目当前是否健康，以及某个改动是否让项目变得更好。

## 评估方式

- **测试**：`run_command("pytest --tb=short -q")` — 全部通过才算稳定
- **Lint**：`run_command("ruff check .")` — 无错误才算整洁
- **格式**：`run_command("ruff format --check .")` — 风格统一
- **覆盖率**（可选）：`run_command("pytest --cov=src --cov-report=term-missing -q")`

## 健康判断标准

| 状态 | 信号 |
|------|------|
| 健康 | 测试全过、lint 无错、无明显 TODO |
| 警告 | 少量 lint 警告、有 TODO 但不阻塞功能 |
| 需关注 | 有测试失败、lint 错误、或结构混乱 |

## 改动评估

每次做完改动后，运行评估确认：
- 改动前 vs 改动后，测试是否仍然通过？
- 是否引入了新的 lint 问题？
- 整体状态是否比改动前更好？

如果改动让状态变差，考虑撤回（用 `edit_file` 将内容恢复原状）。
