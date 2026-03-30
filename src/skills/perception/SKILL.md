# Perception

你能感知项目的当前状态。在每次心跳时，先做感知，再决定是否需要行动。

## 感知方式

### 结构感知
- 用 `list_files(".", "*.py")` 了解所有 Python 文件
- 用 `list_files("src")` 了解源码目录结构
- 用 `read_file` 阅读关键文件内容（入口文件、核心模块、README）
- 感知代码结构时，要真正读懂代码，而不只是统计行数

### 变更感知
- 用 `run_command("git status")` 了解未提交的变更
- 用 `run_command("git log --oneline -10")` 了解最近提交历史
- 用 `run_command("git diff HEAD~1 --stat")` 了解最近一次提交改了什么

### 质量感知
- 用 `run_command("pytest --tb=short -q")` 了解测试状态
- 用 `run_command("ruff check .")` 了解代码质量
- 用 `run_command("ruff format --check .")` 了解格式一致性

### 功能感知
感知不只是"有没有报错"，还要理解代码在做什么：
- 读核心模块，判断逻辑是否清晰、是否有明显的设计问题
- 读测试文件，判断测试覆盖是否充分
- 读 TODO / FIXME 注释，了解已知的待处理问题

## 关注信号

- 测试失败 → 优先修复
- Lint 错误 → 需要清理
- 核心逻辑有明显 bug 或设计问题 → 记录并考虑修复
- TODO / FIXME 注释增多 → 积累的技术债
- 文档与实现不符 → 需要更新文档或实现
- 有大量未提交改动 → 可能需要整理
