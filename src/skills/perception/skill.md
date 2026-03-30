# Perception

你能感知项目的当前状态。在每次心跳时，先做感知，再决定是否需要行动。

## 感知方式

- 用 `run_command("git status")` 了解未提交的变更
- 用 `run_command("git log --oneline -10")` 了解最近提交历史
- 用 `run_command("find . -name '*.py' | grep -v __pycache__ | grep -v .venv | wc -l")` 了解代码规模
- 用 `read_file` 查看关键文件内容（如 README、主入口文件）
- 用 `run_command("pytest --tb=short -q 2>&1 | tail -20")` 了解测试状态
- 用 `run_command("ruff check . 2>&1 | tail -20")` 了解代码质量

## 关注信号

- 有大量未提交改动 → 可能需要整理
- 测试失败 → 需要修复
- Lint 警告增多 → 需要清理
- TODO / FIXME 注释 → 待完成的工作
- 文档缺失 → 需要补充
