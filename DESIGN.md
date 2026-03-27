# Terrarium 技术设计文档

> **Version**: 0.1.0  
> **Last Updated**: 2026-03-26

---

## 一、项目定位

Terrarium 是一个**项目自迭代框架**，让软件项目具备自我感知、自我判断、自我修改的能力。

### 核心理念

- 项目是拥有 AI 认知核心的"生命体"
- Skill 驱动架构，能力可插拔、可演化
- Agent 自主决策，不预设固定流程

### 项目目标

| 目标 | 说明 |
|------|------|
| **自用（Dogfooding）** | Terrarium 管理自身演化 |
| **通用框架** | 任何项目可用，不限语言/框架 |

### 第一阶段（MVP）

**观察 + 分析 + 建议**（不自动修改代码）：

- ✅ Perception — 感知项目状态
- ✅ Memory — 存储观察历史
- ✅ Cognition — 分析问题原因
- ✅ Evaluation — 判断是否需要改进
- ⏸️ Agency — 后续阶段启用

---

## 二、技术选型

| 类别 | 选型 | 说明 |
|------|------|------|
| **语言** | Python 3.11+ | 类型提示完善 |
| **包管理** | uv | 快速现代 |
| **CLI** | Typer | 类型提示驱动 |
| **Web** | FastAPI | Governance API |
| **调度** | APScheduler | 心跳定时 |
| **Git** | GitPython | 状态读取 |
| **LLM** | LangChain 1.2.13 | `create_agent` |
| **存储** | SQLite + YAML | 轻量无依赖 |

### 触发机制

| 方式 | 状态 | 说明 |
|------|------|------|
| 手动 | ✅ MVP | `terrarium observe` |
| 定时 | ✅ MVP | `terrarium watch --interval 30m` |
| 事件 | ⏸️ 后续 | Git hooks、文件监听 |

---

## 三、目录架构

```
terrarium/
├── pyproject.toml
├── src/
│   ├── core/                   # 框架核心
│   │   ├── cli.py              # CLI 命令
│   │   ├── config.py           # 配置管理
│   │   ├── heartbeat.py        # 心跳调度
│   │   ├── agent.py            # LangChain Agent
│   │   └── skill_loader.py     # Skill 加载器
│   │
│   ├── skills/                 # Agent Skills
│   │   ├── perception/
│   │   │   ├── skill.md
│   │   │   └── scripts/
│   │   ├── memory/
│   │   │   ├── skill.md
│   │   │   └── scripts/
│   │   ├── cognition/
│   │   │   └── skill.md
│   │   └── evaluation/
│   │       └── skill.md
│   │
│   ├── models/                 # Pydantic 数据模型
│   └── utils/                  # 工具函数
│
└── tests/
```

### 运行时目录（被管理项目）

```
.terrarium/
├── config.yaml         # 项目配置
├── identity.md         # 项目身份
├── boundaries.yaml     # 边界规则
├── memory/             # 观察记录
└── logs/
```

---

## 四、Agent Skill 设计

### 设计原则

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
| **Perception** | 扫描文件、Git 状态、运行测试 |
| **Memory** | 存储/查询观察历史 |
| **Cognition** | 分析问题、推理原因、生成建议 |
| **Evaluation** | 判断质量、评估健康度 |

---

## 五、Agent 自主调度（LangChain Skills 架构）

基于 [LangChain Skills SQL Assistant](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant) 官方实现模式。

### 核心特性

- **Progressive disclosure**: 系统提示只放 skill descriptions，content 按需加载
- **SkillMiddleware**: 动态注入 skill 目录到系统提示
- **Tool-driven loading**: Agent 通过 `load_skill` 工具加载完整内容

### 架构图

```
┌─────────────────────────────────────────────────────┐
│              用户输入 / 心跳触发                      │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│               LangChain Agent                       │
│                                                     │
│   System Prompt:                                    │
│   - 基础指令                                        │
│   - ## Available Skills (via SkillMiddleware)      │
│     - perception: 扫描项目文件、Git状态...           │
│     - memory: 存储/查询观察历史...                   │
│                                                     │
│   Tools:                                            │
│   - load_skill(name) → 返回完整 skill.md 内容       │
│   - run_script(skill, script, **kwargs)            │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
                    输出结果/报告
```

### Skill 三级结构

```python
class Skill(TypedDict):
    name: str         # 唯一标识: perception, memory, ...
    description: str  # 1-2句简述 (放入系统提示)
    content: str      # 完整内容 (按需加载)
```

### Agent 实现（官方模式）

```python
# src/core/agent.py
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model

# 1. load_skill 工具
@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.
    
    Use this when you need detailed information about how to handle
    a specific type of request.
    """
    loader = SkillLoader(skills_dir)
    skill = loader.load_skill(skill_name)
    if skill:
        return f"Loaded skill: {skill_name}\n\n{skill['content']}"
    available = ", ".join(loader.list_skills())
    return f"Skill '{skill_name}' not found. Available: {available}"

# 2. SkillMiddleware - 注入 skill descriptions
class SkillMiddleware(AgentMiddleware):
    tools = [load_skill]  # 注册工具
    
    def __init__(self, skills: list[Skill]):
        self.skills_prompt = "\n".join(
            f"- **{s['name']}**: {s['description']}" for s in skills
        )
    
    def wrap_model_call(self, request: ModelRequest, handler) -> ModelResponse:
        # 追加 skills 目录到系统提示
        addendum = f"\n\n## Available Skills\n\n{self.skills_prompt}"
        # ... 修改 request.system_message
        return handler(modified_request)

# 3. 创建 Agent
def create_terrarium_agent(config: TerrariumConfig):
    model = init_chat_model(
        config.llm.model,
        api_key=config.llm.get_api_key(),
    )
    
    skills = load_all_skill_metadata()  # name + description
    
    return create_agent(
        model,
        system_prompt=TERRARIUM_SYSTEM_PROMPT,
        middleware=[SkillMiddleware(skills)],
    )
```

### 心跳节律

| 节律 | 频率 | 提示 |
|------|------|------|
| 快速 | 10m | "快速检查，关注显著变化" |
| 标准 | 30m | "检查状态，如有异常请分析" |
| 深度 | 6h | "回顾演化，总结经验" |

---

## 六、配置文件

所有配置统一在 `.terrarium/config.yaml` 中：

```yaml
version: "0.1"

# 项目信息
project:
  type: python
  name: "My Project"

# 心跳配置
heartbeat:
  quick_interval: "10m"
  standard_interval: "30m"
  deep_interval: "6h"
  enabled: true

# 启用的 Skills
skills:
  - perception
  - memory
  - cognition
  - evaluation

# LLM 配置
llm:
  provider: "openai"
  model: "gpt-4o"
  temperature: 0.3
  api_key: "${OPENAI_API_KEY}"  # 支持环境变量

# 感知配置
perception:
  include_patterns:
    - "**/*.py"
    - "**/*.md"
  exclude_patterns:
    - ".git/**"
    - "__pycache__/**"
    - ".terrarium/**"
  commands:
    test: "pytest"
    lint: "ruff check ."

# 边界规则
boundaries:
  files:
    readonly:
      - "pyproject.toml"
      - "LICENSE"
    writable:
      - "src/**/*.py"
      - "tests/**/*.py"
  actions:
    allowed:
      - "edit_file"
      - "create_file"
      - "run_tests"
    forbidden:
      - "delete_file"
      - "git_push"
  changes:
    max_lines_per_change: 100
    require_approval:
      - "changes > 50 lines"
      - "modifies public API"
```

---

## 七、实施阶段

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

## 八、依赖清单

```toml
[project]
name = "terrarium"
version = "0.1.0"
requires-python = ">=3.11"

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

[project.scripts]
terrarium = "core.cli:app"
```

---

## 九、后续方向

1. Vision Skill — UI 分析
2. 多项目管理
3. 分布式心跳
4. 插件市场
5. 演化可视化 Dashboard
