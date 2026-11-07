import assert from "node:assert/strict";
import { appendFileSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { parseJson, runNodeCli, runPythonCli } from "./helpers.js";

function sandboxFor(t) {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-cross-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const home = path.join(sandbox, "home");
  const project = path.join(sandbox, "project");
  mkdirSync(home);
  mkdirSync(project);
  return { home, project };
}

function installArgs(project) {
  return [
    "install", "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--document-profile", "standalone", "--json"
  ];
}

function verifyArgs(project) {
  return [
    "verify", "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--json"
  ];
}

function run(runner, args, { home, project }) {
  const result = runner(args, { cwd: project, home });
  return { result, body: result.stdout.trim() ? parseJson(result.stdout) : null };
}

test("an install by one installer verifies under the other", (t) => {
  const nodeBox = sandboxFor(t);
  const nodeInstall = run(runNodeCli, installArgs(nodeBox.project), nodeBox);
  assert.equal(nodeInstall.result.status, 0, nodeInstall.result.stderr);
  assert.equal(nodeInstall.body.state, "installed");
  const pythonVerify = run(runPythonCli, verifyArgs(nodeBox.project), nodeBox);
  assert.equal(pythonVerify.result.status, 0, pythonVerify.result.stdout + pythonVerify.result.stderr);
  assert.equal(pythonVerify.body.passed, true);

  const pythonBox = sandboxFor(t);
  const pythonInstall = run(runPythonCli, installArgs(pythonBox.project), pythonBox);
  assert.equal(pythonInstall.result.status, 0, pythonInstall.result.stderr);
  assert.equal(pythonInstall.body.state, "installed");
  const nodeVerify = run(runNodeCli, verifyArgs(pythonBox.project), pythonBox);
  assert.equal(nodeVerify.result.status, 0, nodeVerify.result.stdout + nodeVerify.result.stderr);
  assert.equal(nodeVerify.body.passed, true);

  assert.deepEqual(nodeInstall.body.receipt.payload_hashes, pythonInstall.body.receipt.payload_hashes);
});

test("a file corrupted after a Node install fails the Python verify", (t) => {
  const box = sandboxFor(t);
  const install = run(runNodeCli, installArgs(box.project), box);
  assert.equal(install.result.status, 0, install.result.stderr);
  const [relative] = Object.keys(install.body.receipt.payload_hashes);
  appendFileSync(path.join(install.body.target, relative), "\ncorrupted\n");
  const verify = run(runPythonCli, verifyArgs(box.project), box);
  assert.equal(verify.body.passed, false);
  assert.notEqual(verify.result.status, 0);
});
