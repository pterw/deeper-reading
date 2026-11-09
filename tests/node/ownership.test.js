import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {
  existsSync, lstatSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, readlinkSync, realpathSync,
  rmSync, rmdirSync, symlinkSync, writeFileSync
} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {fileURLToPath} from 'node:url';

// Replays the shared ownership table (tests/fixtures/installer-ownership-cases.json, also run by
// tests/installer for the Python installer) against this installer's command line only.
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const CLI = path.join(ROOT, 'installer', 'node', 'cli.js');
const TABLE = JSON.parse(readFileSync(new URL('../fixtures/installer-ownership-cases.json', import.meta.url), 'utf8'));
const STEP_KEYS = {
  mkdir: ['do', 'path'],
  link: ['do', 'at', 'to'],
  rmdir: ['do', 'path'],
  file: ['do', 'path'],
  receipt: ['do', 'path', 'delete', 'set'],
  run: ['do', 'cwd', 'home', 'args', 'expect', 'unchanged', 'survives']
};
const EXPECT_KEYS = ['exit', 'state', 'code', 'code_one_of', 'passed', 'message_has', 'message_lacks'];

// A junction on Windows; the argument is ignored elsewhere, which makes a directory symlink. A relative
// target is written as it stands, as git stores it; a junction cannot be relative, so that is a directory symlink.
function link(at, to) {
  mkdirSync(path.dirname(at), {recursive: true});
  symlinkSync(to, at, path.isAbsolute(to) ? 'junction' : 'dir');
}

// Throws on a step kind, a step key or an expect key the reader does not implement.
function checkStep(step) {
  const allowed = STEP_KEYS[step.do];
  if (!allowed) throw new Error(`unknown step kind: ${step.do}`);
  for (const key of Object.keys(step)) if (!allowed.includes(key)) throw new Error(`unknown step key: ${key}`);
  for (const key of Object.keys(step.expect || {})) {
    if (!EXPECT_KEYS.includes(key)) throw new Error(`unknown expect key: ${key}`);
  }
}

// Paths and links are recorded, never followed, so a link and its target text are compared as written.
function snapshot(directory, found = new Map()) {
  for (const name of readdirSync(directory).sort()) {
    const entry = path.join(directory, name);
    const stat = lstatSync(entry);
    if (stat.isSymbolicLink()) found.set(entry, `link:${readlinkSync(entry)}`);
    else if (stat.isDirectory()) { found.set(entry, 'dir'); snapshot(entry, found); }
    else found.set(entry, createHash('sha256').update(readFileSync(entry)).digest('hex'));
  }
  return found;
}

function replay(caseId, steps, work) {
  const fill = value => value.replaceAll('{work}', work).replaceAll('{home}', path.join(work, 'home'))
    .replaceAll('{project}', path.join(work, 'project'));
  const where = value => path.resolve(fill(value));
  mkdirSync(path.join(work, 'home'));
  for (const step of steps) {
    checkStep(step);
    if (step.do === 'mkdir') mkdirSync(where(step.path), {recursive: true});
    else if (step.do === 'link') link(where(step.at), step.to.startsWith('{') ? where(step.to) : step.to);
    else if (step.do === 'rmdir') rmdirSync(where(step.path));
    else if (step.do === 'file') {
      mkdirSync(path.dirname(where(step.path)), {recursive: true});
      writeFileSync(where(step.path), 'unmanaged\n');
    } else if (step.do === 'receipt') {
      const file = path.join(where(step.path), '.install-receipt.json');
      const receipt = JSON.parse(readFileSync(file, 'utf8'));
      for (const key of step.delete || []) delete receipt[key];
      Object.assign(receipt, step.set || {});
      writeFileSync(file, JSON.stringify(receipt));
    } else runStep(caseId, step, work, where, fill);
  }
}

function runStep(caseId, step, work, where, fill) {
  const home = where(step.home || '{home}');
  const before = snapshot(work);
  const result = spawnSync(process.execPath, [CLI, ...step.args.map(fill), '--json'], {
    cwd: where(step.cwd), encoding: 'utf8', timeout: 60000, env: {...process.env, HOME: home, USERPROFILE: home}
  });
  const label = `${caseId}: ${step.args.join(' ')}`;
  const payload = JSON.parse(result.stdout);
  const {expect} = step;
  assert.equal(result.status, expect.exit, `${label} exit: ${result.stdout}${result.stderr}`);
  if (expect.state === null) assert.equal('state' in payload, false, `${label} has no state: ${result.stdout}`);
  else assert.equal(payload.state, expect.state, label);
  // `code_one_of`: the platforms name this refusal differently.
  if (expect.code_one_of) assert.ok(expect.code_one_of.includes(payload.code), `${label} code ${payload.code}`);
  else assert.equal(payload.code, expect.code, `${label} code`);
  if ('passed' in expect) assert.equal(payload.passed, expect.passed, `${label} passed`);
  for (const text of expect.message_has || []) assert.ok(payload.error.includes(text), `${label}: ${payload.error}`);
  for (const text of expect.message_lacks || []) assert.ok(!payload.error.includes(text), `${label}: ${payload.error}`);
  if (step.unchanged) assert.deepEqual([...snapshot(work)], [...before], `${label} changed the disk`);
  for (const survivor of step.survives || []) assert.ok(existsSync(where(survivor)), `${label}: ${survivor} is gone`);
}

test('table case ids are unique', () => {
  const ids = TABLE.cases.map(item => item.id);
  assert.equal(new Set(ids).size, ids.length);
});

test('the reader rejects a step kind, step key or expect key it does not implement', () => {
  assert.throws(() => checkStep({do: 'teleport'}), /unknown step kind/);
  assert.throws(() => checkStep({do: 'mkdir', path: 'x', mode: 1}), /unknown step key/);
  assert.throws(() => checkStep({do: 'run', expect: {exit: 0, colour: 'red'}}), /unknown expect key/);
  for (const item of TABLE.cases) for (const step of item.steps) checkStep(step);
});

for (const item of TABLE.cases) {
  test(`ownership case ${item.id}`, t => {
    const work = realpathSync.native(mkdtempSync(path.join(os.tmpdir(), 'deeper-reading-owner-')));
    t.after(() => rmSync(work, {recursive: true, force: true}));
    replay(item.id, item.steps, work);
  });
}
