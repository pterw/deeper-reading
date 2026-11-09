import json
from pathlib import Path
import re

import pytest

# Sanity check of the two shared tables the ownership and recovery readers replay
# (python: tests/installer, node: tests/node). It guards the table shape so that a
# reader never passes vacuously on a field it does not implement.
FIXTURES = Path(__file__).parents[1] / 'fixtures'
TABLES = ['installer-ownership-cases.json', 'installer-recovery-cases.json']
STEP_KEYS = {
    'mkdir': {'do', 'path'},
    'link': {'do', 'at', 'to'},
    'rmdir': {'do', 'path'},
    'file': {'do', 'path'},
    'receipt': {'do', 'path', 'delete', 'set'},
    'run': {'do', 'cwd', 'home', 'args', 'expect', 'unchanged', 'survives'},
}
EXPECT_KEYS = {'exit', 'state', 'code', 'passed', 'message_has', 'message_lacks'}
PLACEHOLDERS = {'{work}', '{home}', '{project}'}
# Frozen: an unreadable receipt gets no guard, so the core's error stands and has no code.
# Without a receipt, verify has nothing to guard either: its core failure has no code.
NO_CODE_REFUSALS = {'receipt_unreadable': None, 'project_link_out_no_receipt': {'verify'}}


def has_no_code(case_id, step):
    commands = NO_CODE_REFUSALS.get(case_id, ())
    return commands is None or step['args'][0] in commands
REQUIRED_IDS = {
    'installer-ownership-cases.json': {
        'leaf', 'parent', 'grandparent', 'verify_through_link', 'install_through_link',
        'dry_run_through_link', 'user_request_project_receipt', 'project_into_user',
        'shared_skills_folder', 'project_into_project', 'receipt_target_missing',
        'receipt_target_unknown', 'shared_root', 'linked_home', 'plain', 'dotfiles_parent',
        'receipt_scope_unknown', 'receipt_target_not_string', 'receipt_target_auto',
        'project_sibling_prefix', 'doctor_not_guarded', 'receipt_unreadable',
        'user_scope_ignores_project_dir', 'project_link_out_first_install',
        'project_first_install_inside', 'project_dir_through_link', 'project_dir_not_created',
        'project_dangling_link_out', 'project_dangling_link_skills', 'project_link_out_no_receipt',
        'scope_mismatch_coinciding_roots',
    },
    'installer-recovery-cases.json': {
        'install_claude_user', 'install_claude_project', 'install_codex_user',
        'uninstall_claude_user', 'uninstall_claude_user_force', 'uninstall_codex_user',
        'install_other_user', 'uninstall_other_user', 'uninstall_claude_project',
    },
}


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding='utf-8'))['cases']


def steps(name, kind=None):
    for case in load(name):
        for step in case['steps']:
            if kind is None or step.get('do') == kind:
                yield case['id'], step


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)


@pytest.mark.parametrize('name', TABLES)
def test_ids_are_unique_and_required_ids_present(name):
    ids = [case['id'] for case in load(name)]
    assert len(ids) == len(set(ids))
    assert REQUIRED_IDS[name] <= set(ids)


@pytest.mark.parametrize('name', TABLES)
def test_steps_use_known_kinds_keys_and_placeholders(name):
    for case_id, step in steps(name):
        assert step.get('do') in STEP_KEYS, (case_id, step)
        assert set(step) <= STEP_KEYS[step['do']], (case_id, step)
        if step['do'] == 'receipt':
            assert ('delete' in step) != ('set' in step), (case_id, step)
        if step['do'] == 'run':
            assert set(step['expect']) <= EXPECT_KEYS, (case_id, step)
        for text in strings({k: v for k, v in step.items() if k != 'expect'}):
            assert set(re.findall(r'\{[a-z]+\}', text)) <= PLACEHOLDERS, (case_id, text)


@pytest.mark.parametrize('name', TABLES)
def test_runs_declare_their_outcome(name):
    for case_id, step in steps(name, 'run'):
        assert step['args'] and step['cwd'], case_id
        assert isinstance(step['unchanged'], bool), case_id
        assert isinstance(step['expect']['exit'], int), case_id
        # null means the payload has no state field (a successful verify reports passed).
        assert 'state' in step['expect'], case_id
        # doctor reports neither: it always exits 0 with command "doctor".
        assert step['expect']['state'] or step['expect'].get('passed') is not None or step['args'][0] == 'doctor', case_id


@pytest.mark.parametrize('name', TABLES)
def test_every_refusal_has_a_code_and_leaves_disk_unchanged(name):
    refusals = [(case_id, step) for case_id, step in steps(name, 'run') if step['expect']['exit'] != 0]
    assert refusals
    for case_id, step in refusals:
        assert step['expect']['exit'] == 2, case_id
        # The core's own verify failure carries passed but no state.
        state = None if has_no_code(case_id, step) and step['args'][0] == 'verify' else 'failed'
        assert step['expect']['state'] == state, case_id
        assert bool(step['expect'].get('code')) != has_no_code(case_id, step), case_id
        assert step['unchanged'] is True, case_id


@pytest.mark.parametrize('name', TABLES)
def test_every_case_runs_the_installer(name):
    for case in load(name):
        assert any(step['do'] == 'run' for step in case['steps']), case['id']


@pytest.mark.parametrize('name', TABLES)
def test_refusals_state_what_a_reader_must_check(name):
    for case_id, step in steps(name, 'run'):
        expect = step['expect']
        if expect['exit'] == 0:
            continue
        if step['args'][0] == 'verify':
            assert expect.get('passed') is False, case_id
        if expect.get('code') in ('installer.owner.mismatch', 'installer.project.escape'):
            assert step.get('survives'), case_id
