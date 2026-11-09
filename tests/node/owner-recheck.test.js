import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, symlinkSync, writeFileSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath, pathToFileURL} from 'node:url';

// Two targets can share one skills folder (a linked ~/.claude/skills). Both can pass the
// command-line ownership check before either has written a receipt; the check must repeat
// inside the target lock, where the second one sees the first one's receipt.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CLI = path.join(ROOT, 'installer', 'node', 'cli.js');

// Loaded with `node --import` for the codex run. At the first call of the hooked function, which
// runs between the command-line check and the lock, it installs claude with the real command line
// (a concurrent winner) and records the winner's files.
const PRELOAD = `
import childProcess from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import path from 'node:path';
const {PLANT_CLI, PLANT_MARK, PLANT_SHARED, PLANT_HOOK} = process.env;
const realSpawn = childProcess.spawnSync;
const realMkdir = fs.mkdirSync;
function snap(folder, found = {}) {
  for (const entry of fs.readdirSync(folder, {withFileTypes: true})) {
    const full = path.join(folder, entry.name);
    if (entry.isDirectory()) snap(full, found);
    else found[full] = createHash('sha256').update(fs.readFileSync(full)).digest('hex');
  }
  return found;
}
let planted = false;
function plant() {
  if (planted) return;
  planted = true;
  const env = {...process.env};
  for (const key of ['PLANT_CLI', 'PLANT_MARK', 'PLANT_SHARED', 'PLANT_HOOK']) delete env[key];
  const won = realSpawn(process.execPath, [PLANT_CLI, 'install', '--target', 'claude', '--scope', 'user', '--json'],
    {encoding: 'utf8', env});
  fs.writeFileSync(PLANT_MARK, JSON.stringify({exit: won.status, files: snap(PLANT_SHARED)}));
}
if (PLANT_HOOK === 'spawnSync') childProcess.spawnSync = (...args) => { plant(); return realSpawn(...args); };
else fs.mkdirSync = (...args) => { plant(); return realMkdir(...args); };
syncBuiltinESMExports();
`;

function snapshot(folder, found = {}) {
  for (const entry of readdirSync(folder, {withFileTypes: true})) {
    const full = path.join(folder, entry.name);
    if (entry.isDirectory()) snapshot(full, found);
    else found[full] = createHash('sha256').update(readFileSync(full)).digest('hex');
  }
  return found;
}

// Both commands plant at the lock's parent folder creation, which runs after the command-line check
// and before the lock is taken, so a check moved out of the lock is not caught by the refusal.
for (const [command, hook] of [['install', 'mkdirSync'], ['uninstall', 'mkdirSync']]) {
  test(`${command}: the second target is refused when the first wins after the command-line check`, t => {
    const work = realpathSync.native(mkdtempSync(path.join(os.tmpdir(), 'deeper-reading-recheck-')));
    t.after(() => rmSync(work, {recursive: true, force: true}));
    const home = path.join(work, 'home');
    const shared = path.join(home, '.agents', 'skills');
    mkdirSync(shared, {recursive: true});
    mkdirSync(path.join(home, '.claude'));
    symlinkSync(shared,path.join(home, '.claude', 'skills'), 'junction');
    const preload = path.join(work, 'preload.mjs');
    const mark = path.join(work, 'mark.json');
    writeFileSync(preload, PRELOAD);

    const result = spawnSync(process.execPath, ['--import', pathToFileURL(preload).href, CLI, command, '--target', 'codex', '--scope', 'user', '--json'], {
      cwd: work, encoding: 'utf8', timeout: 120000,
      env: {
        ...process.env, HOME: home, USERPROFILE: home,
        PLANT_CLI: CLI, PLANT_MARK: mark, PLANT_SHARED: shared, PLANT_HOOK: hook
      }
    });

    const winner = JSON.parse(readFileSync(mark, 'utf8'));
    assert.equal(winner.exit, 0, 'the concurrent winner did not install');
    assert.ok(Object.keys(winner.files).length > 0);
    const payload = JSON.parse(result.stdout);
    assert.equal(result.status, 2, result.stdout + result.stderr);
    assert.equal(payload.state, 'failed', result.stdout);
    assert.equal(payload.code, 'installer.owner.mismatch', result.stdout);
    const receipt = JSON.parse(readFileSync(path.join(shared, 'deeper-reading', '.install-receipt.json'), 'utf8'));
    assert.equal(receipt.target, 'claude');
    assert.deepEqual(snapshot(shared), winner.files);
    assert.deepEqual(readdirSync(shared), ['deeper-reading']);
  });
}
