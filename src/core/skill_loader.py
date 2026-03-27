"""Agent Skill loader."""

from pathlib import Path
from typing import Optional


class SkillLoader:
    """Load and manage Agent Skills."""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._cache: dict[str, dict] = {}
    
    def load_skill(self, name: str) -> dict:
        """Load a skill by name."""
        if name in self._cache:
            return self._cache[name]
        
        skill_path = self.skills_dir / name / "skill.md"
        if not skill_path.exists():
            raise ValueError(f"Skill not found: {name}")
        
        content = skill_path.read_text()
        scripts = self._list_scripts(name)
        refs = self._list_refs(name)
        
        skill = {
            "name": name,
            "content": content,
            "scripts": scripts,
            "refs": refs,
            "path": self.skills_dir / name,
        }
        
        self._cache[name] = skill
        return skill
    
    def list_skills(self) -> list[str]:
        """List all available skills."""
        if not self.skills_dir.exists():
            return []
        
        skills = []
        for path in self.skills_dir.iterdir():
            if path.is_dir() and (path / "skill.md").exists():
                skills.append(path.name)
        return sorted(skills)
    
    def _list_scripts(self, name: str) -> list[str]:
        """List scripts for a skill."""
        scripts_dir = self.skills_dir / name / "scripts"
        if not scripts_dir.exists():
            return []
        return sorted([f.name for f in scripts_dir.glob("*.py")])
    
    def _list_refs(self, name: str) -> list[str]:
        """List reference documents for a skill."""
        refs_dir = self.skills_dir / name / "refs"
        if not refs_dir.exists():
            return []
        return sorted([f.name for f in refs_dir.glob("*.md")])
    
    def get_script_path(self, skill_name: str, script_name: str) -> Optional[Path]:
        """Get the full path to a skill script."""
        path = self.skills_dir / skill_name / "scripts" / script_name
        return path if path.exists() else None
