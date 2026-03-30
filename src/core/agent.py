"""Terrarium Agent — loads all skill knowledge at boot, then acts."""

import functools
from pathlib import Path

from src.core.config import TerrariumConfig

SKILLS_DIR = Path(__file__).parent.parent / "skills"


def _extract_summary(content: str) -> str:
    """Extract the first non-heading paragraph from a SKILL.md as its summary."""
    for line in content.strip().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return ""


def get_skill_names() -> list[str]:
    """Return sorted list of available skill names."""
    return sorted(p.parent.name for p in SKILLS_DIR.glob("*/SKILL.md"))


def get_skill_content(name: str) -> str | None:
    """Read the full content of a skill by name. Returns None if not found."""
    skill_file = SKILLS_DIR / name / "SKILL.md"
    if not skill_file.exists():
        return None
    return skill_file.read_text().strip()


@functools.lru_cache(maxsize=1)
def _load_skills() -> str:
    """Build a skill index: name + one-line summary for each skill.

    Cached with ``lru_cache(maxsize=1)`` so tests can call
    ``_load_skills.cache_clear()`` for isolation while production code
    still avoids redundant filesystem I/O.
    """
    lines = []
    for skill_file in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        name = skill_file.parent.name
        summary = _extract_summary(skill_file.read_text())
        lines.append(f"- **{name}**: {summary}")
    if not lines:
        return ""
    header = (
        "## Your Skills\n\n"
        "These are your cognitive and behavioral capabilities. "
        "Use `read_skill(name)` to load the full guide before applying a skill.\n"
    )
    return header + "\n".join(lines)


def _load_identity(project_path: Path) -> str:
    identity_file = project_path / ".terrarium" / "identity.md"
    if not identity_file.exists():
        return ""
    content = identity_file.read_text().strip()
    return f"## Project Identity\n\n{content}" if content else ""


def _build_system_prompt(config: TerrariumConfig, project_path: Path) -> str:
    """Build the static system prompt (skills, identity, drives, boundaries).

    Long-term memory is intentionally excluded — it is injected per-heartbeat
    into the user message so the agent always sees the latest state without
    requiring system-prompt or agent recreation.
    """
    project_name = config.project.name
    parts = [
        f'You are Terrarium — the cognitive core of the project "{project_name}".',
        "You run on a heartbeat. Each time you wake up, you perceive the project's current state, "
        "identify what needs improvement, and act on it. You can read files, edit files, create "
        "files, list files, run commands, and log notes to memory.\n"
        "You have a set of skills — use `read_skill(name)` to load a skill's full guide "
        "before applying it. Don't guess — read the guide first.",
        "When nothing meaningful needs attention, reply with exactly: HEARTBEAT_OK",
    ]

    identity = _load_identity(project_path)
    if identity:
        parts.append(identity)

    if config.drives:
        drive_lines = "\n".join(
            f"- **{d.name}**: {d.description}" for d in config.drives
        )
        parts.append(
            f"## Drives\n\nThese internal tensions motivate your actions:\n\n{drive_lines}"
        )

    readonly = config.boundaries.readonly
    writable = config.boundaries.writable
    boundary_lines = (
        f"- Readonly (never modify): {', '.join(readonly)}\n"
        f"- Writable: {', '.join(writable)}"
    )
    parts.append(f"## Boundaries\n\n{boundary_lines}")

    skills = _load_skills()
    if skills:
        parts.append(skills)

    return "\n\n---\n\n".join(parts)


def create_model(config: TerrariumConfig):
    """Create an LLM instance from config. Reuse this across heartbeats."""
    from langchain.chat_models import init_chat_model

    model_kwargs: dict = {
        "temperature": config.llm.temperature,
    }
    api_key = config.llm.get_api_key()
    if api_key:
        model_kwargs["api_key"] = api_key
    base_url = config.llm.get_base_url()
    if base_url:
        model_kwargs["base_url"] = base_url

    return init_chat_model(config.llm.model, **model_kwargs)


def create_terrarium_agent(config: TerrariumConfig, project_path: Path, *, model=None):
    """Create a Terrarium agent with all skills and tools ready.

    Pass a pre-built *model* to avoid re-initialising the LLM client on every
    heartbeat tick.  When *model* is ``None`` a fresh one is created from config.

    The agent is designed to be created once and invoked repeatedly — the system
    prompt contains only static content (skills, identity, drives, boundaries).
    Dynamic content (memory) is passed per-invocation in the user message.

    Returns the agent object ready to be invoked with
    agent.invoke({"messages": [{"role": "user", "content": "..."}]}).
    """
    from langchain.agents import create_agent

    from src.core.tools import create_tools

    tools = create_tools(project_path, config)

    if model is None:
        model = create_model(config)

    system_prompt = _build_system_prompt(config, project_path)

    agent = create_agent(
        model,
        system_prompt=system_prompt,
        tools=tools,
    )
    return agent
