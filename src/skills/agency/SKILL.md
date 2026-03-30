# Agency

你能在边界约束内修改项目文件。

## 可用动作

- `edit_file(path, old_string, new_string)` — 精确替换文件中的某段内容
- `create_file(path, content)` — 创建新文件
- `run_command(command)` — 运行 shell 命令（测试、lint、格式化等）

## 行动原则

- **精确性**：`edit_file` 的 `old_string` 必须在文件中唯一出现，否则会失败
- **最小改动**：每次只改一个地方，改完用 `run_command` 验证效果
- **先读后改**：改文件前先用 `read_file` 确认文件内容
- **验证改动**：改完代码后运行测试确认没有引入问题

## 典型工作流

```
read_file(path)           # 了解当前内容
edit_file(path, old, new) # 做精确修改
run_command("pytest -q")  # 验证改动正确
memory_log("做了什么")     # 记录此次行动
```
