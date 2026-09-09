from __future__ import annotations

from .base import RuntimeAdapter, VerificationResult
from .claude import ClaudeAdapter
from .codex import CodexAdapter
from .copilot import CopilotAdapter
from .gemini import GeminiAdapter
from .generic_agents import GenericAgentsAdapter

ADAPTERS = {
    'generic-agents': GenericAgentsAdapter,
    'copilot': CopilotAdapter,
    'codex': CodexAdapter,
    'gemini': GeminiAdapter,
    'claude': ClaudeAdapter,
}


def get_adapter(name: str):
    if name not in ADAPTERS:
        raise ValueError(f'unsupported target: {name}')
    return ADAPTERS[name]()


def detect_target() -> str:
    for name in ('copilot', 'gemini', 'codex', 'claude'):
        if ADAPTERS[name]().detect():
            return name
    return 'generic-agents'


__all__ = ['RuntimeAdapter', 'VerificationResult', 'get_adapter', 'detect_target', 'ADAPTERS']
