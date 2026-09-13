import assert from "node:assert/strict";
import { existsSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { parseJson, runNodeCli } from "./helpers.js";

test("doctor is read-only and reports installer and Python states separately", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-cli-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const home = path.join(sandbox, "home");
  mkdirSync(home);
  const result = runNodeCli(["doctor", "--target", "generic-agents", "--json"], {
    home,
    env: { PATH: "" }
  });
  const data = parseJson(result.stdout);
  assert.equal(result.status, 0);
  assert.equal(data.command, "doctor");
  assert.equal(data.installer_status.state, "ready");
  assert.equal(data.python_runtime.state, "blocked");
  assert.equal(data.can_install, true);
  assert.equal(data.can_execute_documents, false);
  assert.equal(data.mutation_performed, false);
  assert.equal(existsSync(path.join(home, ".agents")), false);
});

test("project scope defaults project-dir to cwd and dry-run mutates nothing", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-project-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  mkdirSync(project);
  const result = runNodeCli([
    "install", "--target", "generic-agents", "--scope", "project", "--dry-run", "--json"
  ], { cwd: project, home: path.join(sandbox, "home") });
  const data = parseJson(result.stdout);
  assert.equal(result.status, 0);
  assert.equal(data.state, "dry-run");
  assert.equal(data.target, path.join(project, ".agents", "skills", "deeper-reading"));
  assert.equal(existsSync(data.target), false);
});

test("invalid command emits JSON failure and exit code 2", () => {
  const result = runNodeCli(["explode", "--json"]);
  assert.equal(result.status, 2);
  assert.equal(parseJson(result.stdout).state, "failed");
});

test("verify reports a missing target", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-missing-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  mkdirSync(project);
  const result = runNodeCli([
    "verify", "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--json"
  ], { cwd: project, home: path.join(sandbox, "home") });
  assert.equal(result.status, 2);
  assert.deepEqual(parseJson(result.stdout).violations, ["installation target missing"]);
});

test("explicit project install, verify, and uninstall form one isolated lifecycle", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-lifecycle-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  const home = path.join(sandbox, "home");
  mkdirSync(project);
  mkdirSync(home);
  const common = [
    "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--json"
  ];
  const install = runNodeCli(["install", ...common], { cwd: project, home });
  const target = path.join(project, ".agents", "skills", "deeper-reading");
  assert.equal(install.status, 0, install.stderr);
  assert.equal(existsSync(path.join(target, "SKILL.md")), true);
  const verify = runNodeCli(["verify", ...common], { cwd: project, home });
  assert.equal(verify.status, 0, verify.stderr);
  assert.equal(parseJson(verify.stdout).passed, true);
  const uninstall = runNodeCli(["uninstall", ...common], { cwd: project, home });
  assert.equal(uninstall.status, 0, uninstall.stderr);
  assert.equal(existsSync(path.join(target, "SKILL.md")), false);
});

test("modified managed files require force on uninstall", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-force-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const project = path.join(sandbox, "project");
  mkdirSync(project);
  const common = [
    "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--json"
  ];
  const options = { cwd: project, home: path.join(sandbox, "home") };
  assert.equal(runNodeCli(["install", ...common], options).status, 0);
  const skill = path.join(project, ".agents", "skills", "deeper-reading", "SKILL.md");
  writeFileSync(skill, "modified", "utf8");
  assert.equal(runNodeCli(["uninstall", ...common], options).status, 2);
  assert.equal(runNodeCli(["uninstall", ...common, "--force"], options).status, 0);
});

test("parser rejects unknown, missing-value, and wrong-command options", () => {
  for (const args of [
    ["doctor", "--wat", "--json"],
    ["doctor", "--target", "--json"],
    ["doctor", "--force", "--json"],
    ["verify", "--dry-run", "--json"]
  ]) {
    const result = runNodeCli(args);
    assert.equal(result.status, 2, args.join(" "));
    assert.equal(parseJson(result.stdout).state, "failed");
  }
});

test("help is read-only and exits successfully", () => {
  for (const args of [["--help"], ["install", "--help"]]) {
    const result = runNodeCli(args);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /doctor|install|verify|uninstall/);
  }
});
