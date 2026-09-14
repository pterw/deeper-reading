import assert from 'node:assert/strict';
import childProcess from 'node:child_process';
import {readFileSync} from 'node:fs';
import {syncBuiltinESMExports} from 'node:module';
import test from 'node:test';
import {getAdapter} from '../../installer/node/adapters.js';

const cases = JSON.parse(readFileSync(new URL('../fixtures/discovery-output.json', import.meta.url), 'utf8'));
const actualSpawn = childProcess.spawnSync;
function withResult(result, callback) {
  childProcess.spawnSync = (...args) => { callback?.(...args); return result; };
  syncBuiltinESMExports();
}
function restore() {childProcess.spawnSync = actualSpawn; syncBuiltinESMExports();}

for (const [index, item] of cases.entries()) test(`discovery format ${index}: ${item.host} ${item.state}`, () => {
  const adapter = getAdapter(item.host);
  adapter.detect = () => true;
  try {
    withResult({status:0, stdout:item.output, stderr:''}, (command, args) => {
      assert.equal(command, item.host);
      assert.deepEqual(args, item.host === 'copilot' ? ['skill','list','--json'] : ['skills','list']);
    });
    assert.equal(adapter.discoveryVerify('deeper-reading').state, item.state);
  } finally {restore();}
});

test('spawn failures and optional streams produce useful failure evidence', () => {
  const missing = actualSpawn('deeper-reading-nonexistent-executable-for-test', [], {encoding:'utf8'});
  const timeout = actualSpawn(process.execPath, ['-e','setTimeout(()=>{}, 10000)'], {encoding:'utf8', timeout:100});
  for (const result of [missing, timeout,
    {status:null, stdout:null, stderr:undefined, error:Object.assign(new Error('gone'), {code:'ENOENT'})},
    {status:1, stdout:null, stderr:'permission denied'},
    {status:0, stdout:'[]', stderr:'', error:new Error('transport failed')}]) {
    const adapter = getAdapter('copilot');
    adapter.detect = () => true;
    try {
      withResult(result);
      const discovery = adapter.discoveryVerify('deeper-reading');
      assert.equal(discovery.state, 'failed');
      if (result.error) assert.ok(discovery.evidence.some(item => item.includes(result.error.code || result.error.message)));
    } finally {restore();}
  }
});
