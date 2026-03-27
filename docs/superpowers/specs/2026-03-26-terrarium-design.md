# Terrarium 设计规范

> **Date**: 2026-03-26  
> **Status**: Draft

---

## 概述

Terrarium 是一个项目自迭代框架，让软件项目具备自我感知、自我判断、自我修改的能力。项目作为"生命体"存在，拥有 AI 认知核心，在边界约束内自主演化。

## 目标

1. **自用场景（Dogfooding）**：Terrarium 管理自身演化
2. **通用框架**：任何项目可用，不限语言/框架

## 第一阶段范围（MVP）

**观察 + 分析 + 建议**，不自动修改代码：

- Perception — 感知项目状态
- Memory — 存储观察历史
- Cognition — 分析问题原因
- Evaluation — 判断是否需要改进

> 能思考、能建议，但人来决策

---

## 技术选型

| 类别 | 选型 |
|------|------|
| 语言 | Python 3.11+ |
| 包管理 | uv |
| CLI | Typer |
| Web | FastAPI |
| 调度 | APScheduler |
| Git | GitPython |
| LLM | LangChain 1.2.13 (`create_agent`) |
| 存储 | SQLite + YAML |

---

## 架构设计

### Agent 自主调度

核心理念：**Agent 自主决策，不预设固定流程**

```
用户输入 / 心跳触发
        │
        ▼
┌─────────────────────────────────┐
│       LangChain Agent           │
│                                 │
│  自主决定：                      │
│  - 调用哪些 Skills              │
│  - 什么顺序                     │
│  - 是否迭代                     │
│                                 │
│  ┌────────┐ ┌────────┐         │
│  │Percep- │ │Memory  │ ...     │
│  │tion    │ │        │         │
│  └────────┘ └────────┘         │
└─────────────────────────────────┘
        │
        ▼
   输出结果/报告
```

### Agent Skill 设计原则

- **能力中心化**：每个 Skill 定义"能做什么"
- **去流程化**：不限定 Skill 间的调用关系
- **Agent 自主**：由 Agent 根据任务自行决定调用

### skill.md 格式

```markdown
# <Skill Name>

<简要描述>

## 能力
- 能做什么...

## 触发条件（供 Agent 参考）
- 什么情况下可能需要...

## 可用脚本
- `scripts/xxx.py` - 功能说明

## 输出格式
- 返回格式说明...
```

### 第一阶段 Skills

| Skill | 能力 |
|-------|------|
| Perception | 扫描文件、Git 状态、运行测试 |
| Memory | 存储/查询观察历史 |
| Cognition | 分析问题、推理原因、生成建议 |
| Evaluation | 判断质量、评估健康度 |

---

## 目录结构

```
terrarium/
├── pyproject.toml
├── src/
│   ├── core/                   # 框架核心
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── heartbeat.py
│   │   ├── agent.py
│   │   └── skill_loader.py
│   │
│   ├── skills/                 # Agent Skills
│   │   ├── perception/
│   │   ├── memory/
│   │   ├── cognition/
│   │   └── evaluation/
│   │
│   ├── models/
│   └── utils/
│
└── tests/
```

### 运行时目录（被管理项目）

```
.terrarium/
├── config.yaml
├── identity.md
├── boundaries.yaml
├── memory/
└── logs/
```

---

## 触发机制

| 方式 | 状态 | 说明 |
|------|------|------|
| 手动 | ✅ MVP | `terrarium observe` |
| 定时 | ✅ MVP | `terrarium watch --interval 30m` |
| 事件 | ⏸️ 后续 | Git hooks、文件监听 |

### 心跳节律

| 节律 | 频率 | 提示 |
|------|------|------|
| 快速 | 10m | "快速检查，关注显著变化" |
| 标准 | 30m | "检查状态，如有异常请分析" |
| 深度 | 6h | "回顾演化，总结经验" |

---

## 配置文件

### `.terrarium/config.yaml`

```yaml
version: "0.1"
project_type: python

heartbeat:
  standard_interval: "30m"
  enabled: true

skills:
  - perception
  - memory
  - cognition
  - evaluation

llm:
  provider: "openai"
  model: "gpt-4o"
  api_key: "${OPENAI_API_KEY}"

perception:
  include_patterns: ["**/*.py", "**/*.md"]
  exclude_patterns: [".git/**", "__pycache__/**"]
  commands:
    test: "pytest"
    lint: "ruff check ."
```

### `.terrarium/boundaries.yaml`

```yaml
files:
  readonly: ["pyproject.toml", "LICENSE"]
  writable: ["src/**/*.py", "tests/**/*.py"]

actions:
  allowed: ["edit_file", "create_file", "run_tests"]
  forbidden: ["delete_file", "git_push"]

changes:
  max_lines_per_change: 100
  require_approval: ["changes > 50 lines"]
```

---

## 实施阶段

### Phase 1: Observer（2 周）
- 项目初始化
- CLI 框架（init/observe）
- Skill 加载器
- Perception + Memory Skills
- Heartbeat 循环

### Phase 2: Analyzer（2 周）
- LangChain Agent 集成
- Cognition + Evaluation Skills
- 状态报告生成

### Phase 3: Actor（2 周）
- Boundary + Agency Skills
- Governance API
- 审批流程

### Phase 4: Evolver（2 周）
- Meta-Learning Skill
- 多节律调度
- 演化可视化

---

## 依赖清单

```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "apscheduler>=3.10.0",
    "gitpython>=3.1.0",
    "langchain>=1.2.13",
    "langchain-core>=1.2.22",
    "langchain-openai>=1.1.12",
]
```

---

## 后续方向

1. Vision Skill — UI 分析
2. 多项目管理
3. 分布式心跳
4. 插件市场
5. 演化可视化 Dashboard
