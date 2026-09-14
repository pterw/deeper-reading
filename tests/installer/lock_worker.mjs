import {existsSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {installSkill, uninstallSkill} from '../../installer/node/core.js';
import {loadManifest} from '../../installer/node/manifest.js';
const [packageRoot, targetRoot, barrier, pause] = process.argv.slice(2);
function hook(point) {
  if (point !== pause) return;
  writeFileSync(path.join(barrier, 'ready'), '');
  const deadline = Date.now() + 30000;
  while (!existsSync(path.join(barrier, 'release'))) {
    if (Date.now() > deadline) throw new Error('barrier timeout');
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
  }
  throw new Error('deliberate owner failure');
}
try {
  const result = pause === 'uninstall' ? uninstallSkill(targetRoot) : installSkill({
    packageRoot, targetRoot, manifest: loadManifest(path.join(packageRoot, 'MANIFEST.json')),
    targetName: 'generic-agents', scope: 'user', runtimeProfile: 'standalone',
    documentProfile: 'standalone', documentStatus: {state:'ready', evidence:[], action:[]},
    failureInjector: hook, discoveryVerifier: () => {hook('discovery'); return {state:'not-available'};}
  });
  console.log(JSON.stringify(result));
} catch (error) { console.log(error.message); process.exitCode = 2; }
