import assert from "node:assert/strict";
import { chmodSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { detectTarget, getAdapter } from "../../installer/node/adapters.js";

test("all adapters match the Python user and project roots", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-adapters-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  mkdirSync(project);
  const expected = {
    "generic-agents": [".agents", ".agents"],
    copilot: [".copilot", ".github"],
    codex: [".agents", ".agents"],
    gemini: [".gemini", ".gemini"],
    claude: [".claude", ".claude"]
  };
  for (const [name, [userBase, projectBase]] of Object.entries(expected)) {
    const adapter = getAdapter(name, { homeDir: sandbox });
    assert.equal(adapter.resolveSkillRoot("user", null), path.join(sandbox, userBase, "skills", "deeper-reading"));
    assert.equal(adapter.resolveSkillRoot("project", project), path.join(project, projectBase, "skills", "deeper-reading"));
  }
});

test("project scope requires a concrete project directory", () => {
  const adapter = getAdapter("generic-agents", { homeDir: os.homedir() });
  assert.throws(() => adapter.resolveSkillRoot("project", null), /requires --project-dir/);
});

test("auto detection uses copilot, gemini, codex, claude order", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-path-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const suffix = process.platform === "win32" ? ".cmd" : "";
  const env = { PATH: sandbox, PATHEXT: ".CMD;.EXE" };
  for (const name of ["copilot", "gemini", "codex", "claude"]) {
    const executable = path.join(sandbox, name + suffix);
    writeFileSync(executable, "", "utf8");
    chmodSync(executable, 0o755);
  }
  assert.equal(detectTarget({ env }), "copilot");
  rmSync(path.join(sandbox, `copilot${suffix}`));
  assert.equal(detectTarget({ env }), "gemini");
  rmSync(path.join(sandbox, `gemini${suffix}`));
  assert.equal(detectTarget({ env }), "codex");
  rmSync(path.join(sandbox, `codex${suffix}`));
  assert.equal(detectTarget({ env }), "claude");
  rmSync(path.join(sandbox, `claude${suffix}`));
  assert.equal(detectTarget({ env }), "generic-agents");
});
