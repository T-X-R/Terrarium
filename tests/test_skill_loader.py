# tests/test_skill_loader.py
import pytest
from pathlib import Path
import tempfile

from src.core.skill_loader import SkillLoader


def test_load_skill():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        perception_dir = skills_dir / "perception"
        perception_dir.mkdir(parents=True)
        
        # Create skill.md
        (perception_dir / "skill.md").write_text("""# Perception Skill

感知项目当前状态。

## 能力
- 扫描文件结构
- 获取 Git 状态

## 触发条件
- 当需要了解项目状态时

## 输出格式
返回 ProjectState 对象
""")
        
        # Create scripts
        scripts_dir = perception_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "scan_files.py").write_text("# scan files script")
        
        loader = SkillLoader(skills_dir)
        skill = loader.load_skill("perception")
        
        assert skill["name"] == "perception"
        assert "感知项目" in skill["content"]
        assert "scan_files.py" in skill["scripts"]


def test_load_skill_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = SkillLoader(Path(tmpdir))
        
        with pytest.raises(ValueError, match="Skill not found"):
            loader.load_skill("nonexistent")


def test_list_available_skills():
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        (skills_dir / "perception").mkdir(parents=True)
        (skills_dir / "perception" / "skill.md").write_text("# Perception")
        (skills_dir / "memory").mkdir(parents=True)
        (skills_dir / "memory" / "skill.md").write_text("# Memory")
        
        loader = SkillLoader(skills_dir)
        skills = loader.list_skills()
        
        assert "perception" in skills
        assert "memory" in skills
