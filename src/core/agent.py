"""Terrarium Agent implementation using LangChain Skills architecture.

Based on: https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant
"""

from pathlib import Path
from typing import TypedDict, Callable, Any
import subprocess
import json

from langchain.tools import tool
from langchain.chat_models import init_chat_model

from src.core.config import TerrariumConfig
from src.core.skill_loader import SkillLoader


# Skill 三级结构
class Skill(TypedDict):
    """A skill that can be progressively disclosed to the agent."""
    name: str         # 唯一标识
    description: str  # 1-2句简述 (放入系统提示)
    content: str      # 完整内容 (按需加载)


# 系统提示
TERRARIUM_SYSTEM_PROMPT = """You are Terrarium, a self-iterating project framework agent.

Your role is to observe, analyze, and provide suggestions for the project you are managing.

## Core Behaviors

1. **Observe**: Use perception skill to understand project state
2. **Remember**: Use memory skill to track observation history  
3. **Analyze**: Think about patterns and potential issues
4. **Suggest**: Provide actionable recommendations

## Guidelines

- Always load relevant skills before taking actions
- Use scripts when you need to gather concrete data
- Be concise and actionable in your suggestions
- Do NOT make changes to code in Phase 1 (observation mode only)
"""


# 全局 SkillLoader 实例（由 create_terrarium_agent 初始化）
_skill_loader: SkillLoader | None = None
_project_path: Path | None = None


def _get_skill_loader() -> SkillLoader:
    """Get the global skill loader instance."""
    if _skill_loader is None:
        raise RuntimeError("Agent not initialized. Call create_terrarium_agent first.")
    return _skill_loader


@tool
def load_skill(skill_name: str) -> str:
    """Load the full content of a skill into the agent's context.
    
    Use this when you need detailed information about how to handle
    a specific type of request. This will provide you with comprehensive
    instructions and available scripts for the skill area.
    
    Args:
        skill_name: The name of the skill to load (e.g., "perception", "memory")
    """
    loader = _get_skill_loader()
    
    try:
        skill = loader.load_skill(skill_name)
        scripts_list = "\n".join(f"  - {s}" for s in skill.get("scripts", []))
        return f"""Loaded skill: {skill_name}

{skill['content']}

## Available Scripts
{scripts_list if scripts_list else "  (no scripts)"}
"""
    except ValueError:
        available = ", ".join(loader.list_skills())
        return f"Skill '{skill_name}' not found. Available skills: {available}"


@tool
def run_script(skill_name: str, script_name: str, args: str = "{}", **kwargs) -> str:
    """Run a script from a loaded skill.
    
    Scripts are Python files that perform specific operations like
    scanning files, querying git status, or saving observations.
    
    Args:
        skill_name: The skill containing the script (e.g., "perception")
        script_name: The script filename (e.g., "scan_files.py")  
        args: JSON string of arguments to pass to the script
    """
    # Ignore extra kwargs from LangChain tool invocation
    loader = _get_skill_loader()
    
    script_path = loader.get_script_path(skill_name, script_name)
    if script_path is None:
        return f"Script '{script_name}' not found in skill '{skill_name}'"
    
    try:
        # Parse args
        script_args = json.loads(args) if args else {}
        
        # Add project_path if not provided
        if "project_path" not in script_args and _project_path:
            script_args["project_path"] = str(_project_path)
        
        # Run the script as a module
        # For now, we import and call directly
        import importlib.util
        spec = importlib.util.spec_from_file_location("script", script_path)
        if spec is None or spec.loader is None:
            return f"Failed to load script: {script_path}"
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for a main function or specific function
        if hasattr(module, "main"):
            result = module.main(**script_args)
        elif hasattr(module, script_name.replace(".py", "")):
            func = getattr(module, script_name.replace(".py", ""))
            result = func(**script_args)
        else:
            # Try to find the first callable that matches pattern
            for name in dir(module):
                if not name.startswith("_"):
                    obj = getattr(module, name)
                    if callable(obj) and not isinstance(obj, type):
                        result = obj(**script_args)
                        break
            else:
                return f"No callable function found in {script_name}"
        
        # Format result
        if isinstance(result, dict):
            return json.dumps(result, indent=2, default=str)
        return str(result)
        
    except json.JSONDecodeError as e:
        return f"Invalid JSON args: {e}"
    except Exception as e:
        return f"Script execution error: {e}"


def load_all_skill_metadata(loader: SkillLoader) -> list[Skill]:
    """Load metadata (name + description) for all skills.
    
    Only loads the first few lines of each skill.md to extract description.
    """
    skills: list[Skill] = []
    
    for name in loader.list_skills():
        try:
            skill_data = loader.load_skill(name)
            content = skill_data["content"]
            
            # Extract description from skill.md
            # Look for first paragraph after title
            lines = content.strip().split("\n")
            description = ""
            
            for i, line in enumerate(lines):
                # Skip title line
                if line.startswith("#"):
                    continue
                # Skip empty lines
                if not line.strip():
                    continue
                # First non-empty, non-title line is the description
                description = line.strip()
                break
            
            skills.append(Skill(
                name=name,
                description=description or f"Skill for {name}",
                content=content,
            ))
        except Exception:
            # Skip skills that fail to load
            continue
    
    return skills


def build_system_prompt(base_prompt: str, skills: list[Skill]) -> str:
    """Build the full system prompt with skill descriptions."""
    skills_list = "\n".join(
        f"- **{s['name']}**: {s['description']}" for s in skills
    )
    
    return f"""{base_prompt}

## Available Skills

{skills_list}

Use the `load_skill` tool when you need detailed information about handling a specific type of request.
Use the `run_script` tool to execute scripts from loaded skills.
"""


def create_terrarium_agent(config: TerrariumConfig, project_path: Path):
    """Create a Terrarium agent with skill support.
    
    Args:
        config: Terrarium configuration
        project_path: Path to the project being managed
        
    Returns:
        A LangChain agent ready to process requests
    """
    global _skill_loader, _project_path
    
    # Initialize skill loader
    skills_dir = Path(__file__).parent.parent / "skills"
    _skill_loader = SkillLoader(skills_dir)
    _project_path = project_path
    
    # Load skill metadata
    skills = load_all_skill_metadata(_skill_loader)
    
    # Filter to only enabled skills
    enabled_skills = [s for s in skills if s["name"] in config.skills]
    
    # Build system prompt
    system_prompt = build_system_prompt(TERRARIUM_SYSTEM_PROMPT, enabled_skills)
    
    # Initialize model
    model_kwargs = {
        "api_key": config.llm.get_api_key(),
        "temperature": config.llm.temperature,
    }
    
    # Add base_url if configured (for custom endpoints)
    base_url = config.llm.get_base_url()
    if base_url:
        model_kwargs["base_url"] = base_url
    
    model = init_chat_model(
        config.llm.model,
        **model_kwargs,
    )
    
    # Define tools
    tools = [load_skill, run_script]
    
    # Bind tools to model
    model_with_tools = model.bind_tools(tools)
    
    return {
        "model": model_with_tools,
        "tools": tools,
        "system_prompt": system_prompt,
        "skills": enabled_skills,
    }


def invoke_agent(agent: dict, user_message: str) -> str:
    """Invoke the agent with a user message.
    
    Args:
        agent: Agent dict from create_terrarium_agent
        user_message: The user's input message
        
    Returns:
        The agent's response
    """
    from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
    
    messages = [
        SystemMessage(content=agent["system_prompt"]),
        HumanMessage(content=user_message),
    ]
    
    model = agent["model"]
    tools_map = {t.name: t for t in agent["tools"]}
    
    # Simple agent loop
    max_iterations = 10
    for _ in range(max_iterations):
        response = model.invoke(messages)
        messages.append(response)
        
        # Check for tool calls
        if not response.tool_calls:
            # No more tool calls, return final response
            return response.content
        
        # Execute tool calls
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            
            if tool_name in tools_map:
                tool_result = tools_map[tool_name].invoke(tool_args)
            else:
                tool_result = f"Unknown tool: {tool_name}"
            
            # Add tool result to messages
            from langchain_core.messages import ToolMessage
            messages.append(ToolMessage(
                content=str(tool_result),
                tool_call_id=tool_call["id"],
            ))
    
    return "Agent reached maximum iterations without completing."
