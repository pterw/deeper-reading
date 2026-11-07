import pytest

from installer.adapters.claude import ClaudeAdapter
from installer.adapters.codex import CodexAdapter
from installer.adapters.copilot import CopilotAdapter
from installer.adapters.gemini import GeminiAdapter
from installer.adapters.generic_agents import GenericAgentsAdapter


SKILL = 'deeper-reading'


@pytest.mark.parametrize(
    ('adapter', 'user_base', 'project_base'),
    [
        (GenericAgentsAdapter, '.agents', '.agents'),
        (CopilotAdapter, '.copilot', '.github'),
        (GeminiAdapter, '.gemini', '.gemini'),
        (CodexAdapter, '.agents', '.agents'),
        (ClaudeAdapter, '.claude', '.claude'),
    ],
)
def test_adapter_roots_are_under_the_given_home_and_project(
    adapter, user_base, project_base, tmp_path, monkeypatch
):
    home = tmp_path / 'home'
    project = tmp_path / 'project'
    home.mkdir()
    project.mkdir()
    # Path.home() reads USERPROFILE on Windows and HOME elsewhere.
    monkeypatch.setenv('HOME', str(home))
    monkeypatch.setenv('USERPROFILE', str(home))
    assert adapter().resolve_skill_root('user', None) == home / user_base / 'skills' / SKILL
    assert (
        adapter().resolve_skill_root('project', project)
        == project / project_base / 'skills' / SKILL
    )
