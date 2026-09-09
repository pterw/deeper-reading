from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_canonical_skill_is_at_package_root():
    assert (ROOT / 'SKILL.md').is_file()
    assert not (ROOT / 'skill' / 'SKILL.md').exists()
    assert not (ROOT / 'payload' / 'SKILL.md').exists()


def test_existing_workflow_verifier_remains_runtime_payload():
    assert (ROOT / 'scripts' / 'verify_run.py').is_file()
