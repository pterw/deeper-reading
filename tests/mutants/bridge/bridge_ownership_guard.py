"""Runs the ownership-guard test files of both installers for tests/mutants/ownership-guard.json.

mutate.py runs unittest only, so this one case starts the pytest and node suites as
subprocesses with the repository root as cwd. Named bridge_* so pytest does not collect it.

The suites run in order and stop at the first failure: one failure is enough to catch a planted
defect, and each defect otherwise pays for all four suites, which brought the gate to its time limit.
"""

from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
TIMEOUT = 300
SUITES = (
    [sys.executable, '-m', 'pytest', '-q', '-x', 'tests/installer/test_ownership.py'],
    [sys.executable, '-m', 'pytest', '-q', '-x', 'tests/installer/test_owner_recheck.py'],
    ['node', '--test', 'tests/node/ownership.test.js'],
    ['node', '--test', 'tests/node/owner-recheck.test.js'],
)


class OwnershipGuardSuites(unittest.TestCase):
    def test_suites_pass(self):
        for command in SUITES:
            result = subprocess.run(
                command, cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT, check=False
            )
            self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr[-2000:])


if __name__ == '__main__':
    unittest.main()
