# Memory Skill

存储和检索项目观察历史。

## 能力

- 保存观察记录到数据库
- 查询历史观察记录
- 按时间范围筛选

## 触发条件

- 当需要保存当前观察结果时
- 当需要查询历史数据进行对比时
- 当需要分析趋势时

## 可用脚本

- `scripts/save_observation.py` - 保存观察记录
- `scripts/query_history.py` - 查询历史记录

## 输出格式

保存：返回观察记录 ID
查询：返回 Observation 列表
