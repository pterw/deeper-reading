from layout import ROOT, SKILL_ROOT


def test_canonical_skill_is_at_package_root():
    assert (SKILL_ROOT / 'SKILL.md').is_file()
    assert not (ROOT / 'SKILL.md').exists()
    assert not (ROOT / 'skill' / 'SKILL.md').exists()
    assert not (ROOT / 'payload' / 'SKILL.md').exists()


def test_existing_workflow_verifier_remains_runtime_payload():
    assert (SKILL_ROOT / 'scripts' / 'verify_run.py').is_file()


def test_skill_license_is_a_regular_copy_of_the_root_license():
    copy = SKILL_ROOT / 'LICENSE'
    assert copy.is_file() and not copy.is_symlink()
    assert copy.read_bytes() == (ROOT / 'LICENSE').read_bytes()
