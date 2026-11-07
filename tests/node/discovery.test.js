import assert from 'node:assert/strict';
import childProcess from 'node:child_process';
import {chmodSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {getAdapter, hostPathRefusal, resolveCommand, unsafeShimPath, usablePathDirectory} from '../../installer/node/adapters.js';

const cases = JSON.parse(readFileSync(new URL('../fixtures/discovery-output.json', import.meta.url), 'utf8'));
const actualSpawn = childProcess.spawnSync;
const WIN = process.platform === 'win32';
// One table for both runtimes (tests/installer/test_discovery.py reads the same file).
const resolution = JSON.parse(readFileSync(new URL('../fixtures/host-resolution-cases.json', import.meta.url), 'utf8'));
const REFUSED = resolution.refusal_characters;
function withResult(result) {childProcess.spawnSync = () => result; syncBuiltinESMExports();}
function restore() {childProcess.spawnSync = actualSpawn; syncBuiltinESMExports();}
function tempDir(t, ...parts) {
  const root = mkdtempSync(path.join(os.tmpdir(), 'deeper-reading-discovery-'));
  t.after(() => rmSync(root, {recursive: true, force: true}));
  const directory = path.join(root, ...parts);
  mkdirSync(directory, {recursive: true});
  return directory;
}
function envFor(directory) {return {...process.env, PATH: directory + path.delimiter + (process.env.PATH || '')};}

// A host that only records its argument vector and prints `output` (the parser input).
function writeShim(directory, host, output) {
  writeFileSync(path.join(directory, 'out.txt'), output);
  const shim = path.join(directory, WIN ? `${host}.cmd` : host);
  writeFileSync(shim, WIN
    ? '@echo off\r\necho %*> "%~dp0argv.txt"\r\ntype "%~dp0out.txt"\r\n'
    : '#!/bin/sh\nd=$(dirname "$0")\nprintf "%s" "$*" > "$d/argv.txt"\ncat "$d/out.txt"\n');
  chmodSync(shim, 0o755);
  return shim;
}
// An inert executable: resolvable, never run because spawnSync is patched.
function stubHost(t, host) {
  const directory = tempDir(t, 'bin');
  const file = path.join(directory, WIN ? `${host}.exe` : host);
  writeFileSync(file, '');
  chmodSync(file, 0o755);
  return envFor(directory);
}

const SHIM_OUTPUT = {
  copilot: '[{"name":"deeper-reading","enabled":true}]',
  gemini: 'Discovered Agent Skills:\n\ndeeper-reading [Enabled]\n  Description: Read\n  Location:    /skills/deeper-reading\n\n'
};
const SHIM_ARGV = {copilot: 'skill list --json', gemini: 'skills list'};

for (const host of ['copilot', 'gemini']) test(`discovery starts a real host shim: ${host}`, t => {
  const directory = tempDir(t, 'host dir');
  writeShim(directory, host, SHIM_OUTPUT[host]);
  const discovery = getAdapter(host, {env: envFor(directory)}).discoveryVerify('deeper-reading');
  assert.equal(discovery.state, 'verified', JSON.stringify(discovery.evidence));
  assert.equal(readFileSync(path.join(directory, 'argv.txt'), 'utf8').trim(), SHIM_ARGV[host]);
});

for (const [index, item] of cases.entries()) test(`discovery format ${index}: ${item.host} ${item.state}`, t => {
  const adapter = getAdapter(item.host, {env: stubHost(t, item.host)});
  try {
    withResult({status:0, stdout:item.output, stderr:''});
    assert.equal(adapter.discoveryVerify('deeper-reading').state, item.state);
  } finally {restore();}
});

test('spawn failures and optional streams produce useful failure evidence', t => {
  const missing = actualSpawn('deeper-reading-nonexistent-executable-for-test', [], {encoding:'utf8'});
  const timeout = actualSpawn(process.execPath, ['-e','setTimeout(()=>{}, 10000)'], {encoding:'utf8', timeout:100});
  const adapter = getAdapter('copilot', {env: stubHost(t, 'copilot')});
  for (const result of [missing, timeout,
    {status:null, stdout:null, stderr:undefined, error:Object.assign(new Error('gone'), {code:'ENOENT'})},
    {status:1, stdout:null, stderr:'permission denied'},
    {status:0, stdout:'[]', stderr:'', error:new Error('transport failed')}]) {
    try {
      withResult(result);
      const discovery = adapter.discoveryVerify('deeper-reading');
      assert.equal(discovery.state, 'failed');
      if (result.error) assert.ok(discovery.evidence.some(item => item.includes(result.error.code || result.error.message)));
    } finally {restore();}
  }
});

test('unsafeShimPath returns the first offending character of the refusal set', () => {
  for (const character of REFUSED) assert.equal(unsafeShimPath(`C:\\npm\\a${character}b\\copilot.cmd`), character);
  assert.equal(unsafeShimPath('C:\\npm prefix\\copilot.cmd'), null);
  assert.equal(unsafeShimPath('C:\\a%b&c\\copilot.cmd'), '%');
});

const HOST = WIN ? 'win32' : 'posix';
const hostRows = resolution.path_entries.filter(row => (row.platform ?? HOST) === HOST);
test('path entry table has rows for this host', () => assert.ok(hostRows.length > 0));
for (const row of hostRows) test(`path entry usability: ${row.entry}`, () => {
  assert.equal(usablePathDirectory(row.entry, WIN) !== null, row.usable);
});

for (const item of resolution.cases) test(`host resolution table: ${item.id}`, t => {
  const root = path.join(tempDir(t, 'root'));
  mkdirSync(path.join(root, 'cwd'), {recursive: true});
  for (const directory of item.dirs) mkdirSync(path.join(root, directory), {recursive: true});
  for (const file of item.files) {
    mkdirSync(path.dirname(path.join(root, file)), {recursive: true});
    writeFileSync(path.join(root, file), '');
  }
  const previous = process.cwd();
  const env = {PATH: item.path.map(entry => entry.replaceAll('{root}', root.replaceAll('\\', '/'))).join(';'), PATHEXT: item.pathext};
  let resolved;
  process.chdir(path.join(root, 'cwd'));
  try {resolved = resolveCommand(item.name, {env, platform: 'win32'});} finally {process.chdir(previous);}
  const refusal = resolved && hostPathRefusal(resolved, 'win32');
  assert.equal(resolved ? path.relative(root, resolved).replaceAll('\\', '/') : null, item.resolved);
  assert.equal(Boolean(refusal), item.refusal);
});

for (const directoryName of ['a&b', 'p%q']) test(`a shim in a directory named ${directoryName} is detected but not launched`, t => {
  const directory = tempDir(t, directoryName);
  if (!WIN) return assert.equal(unsafeShimPath(path.join(directory, 'copilot.cmd')), directoryName[1]);
  writeFileSync(path.join(directory, 'copilot.cmd'), '@echo off\r\necho x> "%~dp0marker.txt"\r\n');
  const adapter = getAdapter('copilot', {env: envFor(directory)});
  assert.equal(adapter.detect(), true);
  const discovery = adapter.discoveryVerify('deeper-reading');
  assert.equal(discovery.state, 'failed');
  assert.match(discovery.evidence[0], /unsafe host command path/);
  assert.equal(existsSync(path.join(directory, 'marker.txt')), false);
  assert.equal(existsSync(path.join(directory, '..', 'b', 'marker.txt')), false);
});
