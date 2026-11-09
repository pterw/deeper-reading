import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

// Pins the tree the real package installs to the file list that 0.2.5 installed
// (tests/fixtures/installed-files-0.2.5.json), so a change to the source layout cannot
// silently change what lands in a user's skill folder. The package root comes from this
// file's own path, so the pin holds before and after the source files move.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CLI = path.join(ROOT, 'installer', 'node', 'cli.js');
const PIN = JSON.parse(readFileSync(new URL('../fixtures/installed-files-0.2.5.json', import.meta.url), 'utf8'));
const RECEIPT = '.install-receipt.json';

// Every file under dir as a sorted POSIX path relative to dir.
function filesUnder(dir) {
  return readdirSync(dir, {recursive: true, withFileTypes: true})
    .filter((entry) => entry.isFile())
    .map((entry) => path.relative(dir, path.join(entry.parentPath ?? entry.path, entry.name)).split(path.sep).join('/'))
    .sort();
}

test('installed tree matches the 0.2.5 file list', () => {
  const work = mkdtempSync(path.join(os.tmpdir(), 'dr-installed-tree-'));
  try {
    const home = path.join(work, 'home');
    const project = path.join(work, 'project');
    mkdirSync(home);
    mkdirSync(project);
    const result = spawnSync(process.execPath, [
      CLI, 'install', '--target', 'generic-agents', '--scope', 'project', '--project-dir', project, '--json'
    ], {cwd: work, env: {...process.env, HOME: home, USERPROFILE: home}, encoding: 'utf8', timeout: 120000});
    assert.equal(result.status, 0, result.stdout + result.stderr);

    const target = path.join(project, '.agents', 'skills', 'deeper-reading');
    assert.deepEqual(filesUnder(target).filter((name) => name !== RECEIPT), PIN);
  } finally {
    rmSync(work, {recursive: true, force: true});
  }
});
