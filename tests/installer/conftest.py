import pytest


@pytest.fixture(autouse=True)
def _run_in_tmp_cwd(tmp_path, monkeypatch):
    """Run each test with its own tmp_path as the current directory.

    A containment regression that resolves a receipt path against the current
    directory then lands in tmp, never in the repository.
    """
    monkeypatch.chdir(tmp_path)
