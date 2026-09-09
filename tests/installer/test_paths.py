from pathlib import Path

from installer.adapters.claude import ClaudeAdapter
from installer.adapters.codex import CodexAdapter
from installer.adapters.copilot import CopilotAdapter
from installer.adapters.gemini import GeminiAdapter
from installer.adapters.generic_agents import GenericAgentsAdapter


SKILL = 'deeper-reading'


def assert_target(adapter, tmp_path: Path, monkeypatch):
    home = tmp_path / 'home'
    project = tmp_path / 'project'
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv('HOME', str(home))
    user_root = adapter.resolve_skill_root('user', None)
    project_root = adapter.resolve_skill_root('project', project)
    assert user_root.name == SKILL
    assert project_root.name == SKILL
    assert user_root.parent.name == 'skills'
    assert project_root.parent.name == 'skills'


def test_generic_paths(tmp_path, monkeypatch):
    assert_target(GenericAgentsAdapter(), tmp_path, monkeypatch)
    assert '.agents' in str(GenericAgentsAdapter().resolve_skill_root('project', tmp_path))


def test_copilot_paths(tmp_path, monkeypatch):
    assert_target(CopilotAdapter(), tmp_path, monkeypatch)
    assert '.copilot' in str(CopilotAdapter().resolve_skill_root('user', None))
    assert '.github' in str(CopilotAdapter().resolve_skill_root('project', tmp_path))


def test_gemini_paths(tmp_path, monkeypatch):
    assert_target(GeminiAdapter(), tmp_path, monkeypatch)
    assert '.gemini' in str(GeminiAdapter().resolve_skill_root('user', None))
    assert '.gemini' in str(GeminiAdapter().resolve_skill_root('project', tmp_path))


def test_codex_uses_cross_runtime_agents_path(tmp_path, monkeypatch):
    assert_target(CodexAdapter(), tmp_path, monkeypatch)
    assert '.agents' in str(CodexAdapter().resolve_skill_root('user', None))


def test_claude_paths(tmp_path, monkeypatch):
    assert_target(ClaudeAdapter(), tmp_path, monkeypatch)
    assert '.claude' in str(ClaudeAdapter().resolve_skill_root('user', None))
    assert '.claude' in str(ClaudeAdapter().resolve_skill_root('project', tmp_path))
