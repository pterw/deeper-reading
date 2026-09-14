import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT/'installer'/'install.py'


def run_cli(tmp_path: Path, *args):
    env = os.environ.copy()
    env['HOME'] = str(tmp_path/'home')
    env['USERPROFILE'] = str(tmp_path/'home')
    (tmp_path/'home').mkdir(exist_ok=True)
    return subprocess.run([sys.executable, str(CLI), *args], cwd=ROOT, env=env, capture_output=True, text=True)


def test_doctor_json_is_read_only_and_reports_target(tmp_path):
    proc = run_cli(tmp_path, 'doctor', '--target', 'generic-agents', '--json')
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data['target'] == 'generic-agents'
    assert data['mutation_performed'] is False
    assert not (tmp_path/'home'/'.agents').exists()


def test_verify_missing_install_returns_nonzero_json(tmp_path):
    proc = run_cli(tmp_path, 'verify', '--target', 'generic-agents', '--json')
    assert proc.returncode != 0
    data = json.loads(proc.stdout)
    assert data['passed'] is False


def test_install_dry_run_never_creates_skill_directory(tmp_path):
    proc = run_cli(tmp_path, 'install', '--target', 'generic-agents', '--dry-run', '--json')
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data['state'] == 'dry-run'
    assert not (tmp_path/'home'/'.agents').exists()
