import assert from "node:assert/strict";
import { existsSync, mkdtempSync, mkdirSync, rmSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { parseJson, runNodeCli, runPythonCli } from "./helpers.js";

const OAI_NATIVE_ROOTS = ["/home/oai/skills/pdfs", "/home/oai/skills/docx"];
const BASE = ["--target", "generic-agents", "--scope", "project", "--json"];

// Compared fields are state, exit code, document_status.action and the presence of
// `error`; message wording and the other result keys are deliberately not compared.
const CASES = [
  { name: "dry-run", args: ["install", "--document-profile", "standalone", "--dry-run"], state: "dry-run", code: 0 },
  { name: "blocked oai-native install", args: ["install", "--document-profile", "oai-native"], state: "blocked", code: 2, blocked: true },
  { name: "verify of a missing target", args: ["verify"], code: 2 },
  { name: "uninstall with no receipt", args: ["uninstall"], state: "failed", code: 2 },
  { name: "doctor with oai-native", args: ["doctor", "--document-profile", "oai-native"], code: 0, blocked: true }
];

function comparable(value) {
  return {
    state: value.state,
    action: value.document_status?.action,
    has_error: "error" in value
  };
}

for (const { name, args, state, code, blocked } of CASES) {
  test(`Node and Python agree on ${name}`, (t) => {
    const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-parity-"));
    t.after(() => rmSync(sandbox, { recursive: true, force: true }));
    const project = path.join(sandbox, "project");
    const home = path.join(sandbox, "home");
    mkdirSync(project);
    mkdirSync(home);
    if (blocked) {
      for (const root of OAI_NATIVE_ROOTS) {
        assert.equal(existsSync(root), false, `precondition: ${root} must be absent`);
      }
    }
    const full = [...args, ...BASE, "--project-dir", project];
    const nodeResult = runNodeCli(full, { cwd: project, home });
    const pythonResult = runPythonCli(full, { cwd: project, home });
    assert.equal(nodeResult.status, code, nodeResult.stderr);
    assert.equal(pythonResult.status, code, pythonResult.stderr);
    const nodeJson = parseJson(nodeResult.stdout);
    const pythonJson = parseJson(pythonResult.stdout);
    assert.deepEqual(comparable(nodeJson), comparable(pythonJson));
    if (state) assert.equal(nodeJson.state, state);
    if (blocked) assert.ok(nodeJson.document_status.action.length > 0);
    if (name === "dry-run") {
      const select = (v) => ({
        target: path.resolve(v.target),
        payload_files: [...v.payload_files].sort(),
        stale_owned_files: [...v.stale_owned_files].sort(),
        document_profile: v.document_profile
      });
      assert.deepEqual(select(nodeJson), select(pythonJson));
      assert.equal(existsSync(path.join(project, ".agents")), false);
    }
  });
}
