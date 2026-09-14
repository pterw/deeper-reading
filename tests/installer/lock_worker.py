"""Separate-process transaction driver shared by concurrency tests."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from installer.core import install_skill, uninstall_skill
from installer.manifest import load_manifest
from installer.prerequisites import PrerequisiteStatus
from installer.adapters.base import VerificationResult

package, target, barrier, pause = sys.argv[1:]
package, target, barrier = Path(package), Path(target), Path(barrier)

def hook(point):
    if point != pause:
        return
    (barrier / 'ready').touch()
    deadline = time.monotonic() + 30
    while not (barrier / 'release').exists():
        if time.monotonic() > deadline:
            raise RuntimeError('barrier timeout')
        time.sleep(.01)
    raise RuntimeError('deliberate owner failure')

def discovery(name):
    hook('discovery')
    return VerificationResult('not-available', ())

try:
    if pause == 'uninstall':
        result = uninstall_skill(target)
    else:
        result = install_skill(package, target, load_manifest(package / 'MANIFEST.json'),
            target_name='generic-agents', scope='user', runtime_profile='standalone',
            document_profile='standalone', document_status=PrerequisiteStatus('ready'),
            failure_injector=hook, discovery_verifier=discovery)
    print(json.dumps(result))
except Exception as exc:
    print(str(exc))
    sys.exit(2)
