import json
from pathlib import Path
import subprocess
from unittest.mock import patch

import pytest
from installer.adapters.copilot import CopilotAdapter
from installer.adapters.gemini import GeminiAdapter

CASES = json.loads((Path(__file__).parents[1] / 'fixtures/discovery-output.json').read_text(encoding='utf-8'))

@pytest.mark.parametrize('case', CASES)
def test_discovery_requires_exact_enabled_record(case):
    adapter = CopilotAdapter() if case['host'] == 'copilot' else GeminiAdapter()
    result = subprocess.CompletedProcess([], 0, case['output'], '')
    with patch.object(adapter, 'detect', return_value=True), patch('subprocess.run', return_value=result) as run:
        assert adapter.discovery_verify('deeper-reading').state == case['state']
        expected = ['copilot','skill','list','--json'] if case['host'] == 'copilot' else ['gemini','skills','list']
        assert run.call_args.args[0] == expected

@pytest.mark.parametrize('adapter_type', [CopilotAdapter, GeminiAdapter])
@pytest.mark.parametrize('error', [FileNotFoundError('missing executable'), subprocess.TimeoutExpired('host', 30)])
def test_discovery_process_failure_is_diagnostic(adapter_type, error):
    adapter = adapter_type()
    with patch.object(adapter, 'detect', return_value=True), patch('subprocess.run', side_effect=error):
        result = adapter.discovery_verify('deeper-reading')
    assert result.state == 'failed'
    assert result.evidence
