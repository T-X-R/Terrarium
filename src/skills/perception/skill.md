# Perception Skill

感知项目当前状态，收集文件结构、Git 变更等信息。

## 能力

- 扫描项目文件结构
- 获取 Git 仓库状态
- 统计文件类型分布

## 触发条件

- 当需要了解项目当前状态时
- 当用户询问项目健康度时
- 心跳触发时

## 可用脚本

- `scripts/scan_files.py` - 扫描项目文件，返回文件统计
- `scripts/git_status.py` - 获取 Git 状态

## 输出格式

返回 ProjectState 对象，包含：
- files: 文件统计
- git: Git 状态
- timestamp: 感知时间
