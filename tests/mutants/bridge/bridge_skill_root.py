"""Runs the skill.root validation test files of both installers for tests/mutants/skill-root.json.

mutate.py runs unittest only, so this one case starts the pytest and node suites as
subprocesses with the repository root as cwd. Named bridge_* so pytest does not collect it.
"""

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
TIMEOUT = 300


class SkillRootSuites(unittest.TestCase):
    def run_suite(self, command):
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT, check=False
        )
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])

    def test_python_manifest_validation(self):
        self.run_suite([sys.executable, '-m', 'pytest', '-q', 'tests/installer/test_manifest.py'])

    def test_node_manifest_validation(self):
        self.run_suite(['node', '--test', 'tests/node/manifest.test.js'])


if __name__ == '__main__':
    unittest.main()
