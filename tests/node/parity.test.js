import assert from "node:assert/strict";
import { existsSync, mkdtempSync, mkdirSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { parseJson, runNodeCli, runPythonCli } from "./helpers.js";

test("Node and Python emit the same dry-run transaction plan", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-parity-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  const home = path.join(sandbox, "home");
  mkdirSync(project);
  mkdirSync(home);
  const args = [
    "install", "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--document-profile", "standalone", "--dry-run", "--json"
  ];
  const nodeResult = runNodeCli(args, { cwd: project, home });
  const pythonResult = runPythonCli(args, { cwd: project, home });
  assert.equal(nodeResult.status, 0, nodeResult.stderr);
  assert.equal(pythonResult.status, 0, pythonResult.stderr);
  const select = (value) => ({
    state: value.state,
    target: path.resolve(value.target),
    payload_files: [...value.payload_files].sort(),
    stale_owned_files: [...value.stale_owned_files].sort(),
    document_profile: value.document_profile
  });
  assert.deepEqual(select(parseJson(nodeResult.stdout)), select(parseJson(pythonResult.stdout)));
  assert.equal(existsSync(path.join(project, ".agents")), false);
});
