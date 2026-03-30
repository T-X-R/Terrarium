"""Tests for agent prompt-building functions (no LLM calls)."""

from src.core.agent import (
    _build_system_prompt,
    _extract_summary,
    _load_identity,
    _load_skills,
    get_skill_content,
    get_skill_names,
)
from src.core.config import DriveConfig, TerrariumConfig
from src.core.memory import load_long_term_memory


class TestExtractSummary:
    def test_extracts_first_paragraph(self):
        content = "# Perception\n\n你能感知项目的当前状态。\n\n## 详细内容\n更多..."
        assert _extract_summary(content) == "你能感知项目的当前状态。"

    def test_skips_headings(self):
        content = "# Title\n## Subtitle\nActual content here."
        assert _extract_summary(content) == "Actual content here."

    def test_empty_content(self):
        assert _extract_summary("") == ""

    def test_only_headings(self):
        assert _extract_summary("# Title\n## Subtitle") == ""


class TestLoadSkills:
    def test_returns_index_not_full_content(self):
        result = _load_skills()
        assert "## Your Skills" in result
        assert "read_skill" in result
        for name in get_skill_names():
            assert f"**{name}**" in result

    def test_does_not_contain_full_skill_sections(self):
        result = _load_skills()
        assert "## 感知方式" not in result
        assert "## 可用动作" not in result
        assert "## 评估方式" not in result


class TestGetSkillContent:
    def test_existing_skill(self):
        content = get_skill_content("perception")
        assert content is not None
        assert "感知" in content

    def test_nonexistent_skill(self):
        assert get_skill_content("nonexistent_skill") is None


class TestLoadIdentity:
    def test_returns_empty_when_no_file(self, tmp_path):
        assert _load_identity(tmp_path) == ""

    def test_returns_empty_when_file_is_empty(self, tmp_path):
        identity_file = tmp_path / ".terrarium" / "identity.md"
        identity_file.parent.mkdir(parents=True)
        identity_file.write_text("")
        assert _load_identity(tmp_path) == ""

    def test_loads_identity(self, tmp_path):
        identity_file = tmp_path / ".terrarium" / "identity.md"
        identity_file.parent.mkdir(parents=True)
        identity_file.write_text("# I am a CLI tool\n\nI value simplicity.")

        result = _load_identity(tmp_path)
        assert "## Project Identity" in result
        assert "I am a CLI tool" in result
        assert "I value simplicity" in result


class TestLoadLongTermMemory:
    def test_returns_empty_when_no_file(self, tmp_path):
        assert load_long_term_memory(tmp_path) == ""

    def test_returns_empty_when_file_is_empty(self, tmp_path):
        mem_file = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text("   \n  ")
        assert load_long_term_memory(tmp_path) == ""

    def test_loads_memory(self, tmp_path):
        mem_file = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text("# Long-Term Memory\n\n- always run tests")

        result = load_long_term_memory(tmp_path)
        assert "## Long-Term Memory" in result
        assert "always run tests" in result


class TestBuildSystemPrompt:
    def test_contains_project_name(self, tmp_path):
        config = TerrariumConfig(project={"name": "Terrarium"})
        prompt = _build_system_prompt(config, tmp_path)
        assert "Terrarium" in prompt

    def test_contains_heartbeat_ok_instruction(self, tmp_path):
        config = TerrariumConfig()
        prompt = _build_system_prompt(config, tmp_path)
        assert "HEARTBEAT_OK" in prompt

    def test_includes_drives(self, tmp_path):
        config = TerrariumConfig(
            drives=[
                DriveConfig(name="stability", description="tests must pass"),
                DriveConfig(name="clarity", description="code should be readable"),
            ]
        )
        prompt = _build_system_prompt(config, tmp_path)
        assert "stability" in prompt
        assert "tests must pass" in prompt
        assert "clarity" in prompt

    def test_includes_boundaries(self, tmp_path):
        config = TerrariumConfig()
        prompt = _build_system_prompt(config, tmp_path)
        assert "pyproject.toml" in prompt
        assert "src/**" in prompt

    def test_includes_identity_when_present(self, tmp_path):
        identity_file = tmp_path / ".terrarium" / "identity.md"
        identity_file.parent.mkdir(parents=True)
        identity_file.write_text("I am a web app.")

        config = TerrariumConfig()
        prompt = _build_system_prompt(config, tmp_path)
        assert "I am a web app" in prompt

    def test_system_prompt_excludes_long_term_memory(self, tmp_path):
        mem_file = tmp_path / ".terrarium" / "memory" / "MEMORY.md"
        mem_file.parent.mkdir(parents=True)
        mem_file.write_text("- LTM_EXCLUSION_MARKER_XQ9Z")

        config = TerrariumConfig()
        prompt = _build_system_prompt(config, tmp_path)
        assert "LTM_EXCLUSION_MARKER_XQ9Z" not in prompt
        assert "## Long-Term Memory" not in prompt

    def test_no_drives_section_when_empty(self, tmp_path):
        config = TerrariumConfig(drives=[])
        prompt = _build_system_prompt(config, tmp_path)
        assert "## Drives" not in prompt
