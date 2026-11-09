from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_posix_wrapper_is_thin_delegate():
    text = (ROOT/'installer'/'install.sh').read_text(encoding='utf-8')
    assert 'install.py' in text
    assert 'curl ' not in text
    assert 'git clone' not in text
    assert 'pip install' not in text


def test_powershell_wrapper_is_thin_delegate():
    text = (ROOT/'installer'/'install.ps1').read_text(encoding='utf-8')
    assert 'install.py' in text
    assert 'Invoke-WebRequest' not in text
    assert 'git clone' not in text
    assert 'pip install' not in text
