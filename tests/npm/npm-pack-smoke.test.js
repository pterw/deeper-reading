import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  rmSync
} from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { loadManifest, payloadFiles } from "../../installer/node/manifest.js";
import { npmCommand, npxCommand, parseJson, ROOT } from "../node/helpers.js";

function portable(relativePath) {
  return relativePath.split(path.sep).join("/");
}

function regularFiles(root) {
  const files = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const candidate = path.join(root, entry.name);
    if (entry.isDirectory()) files.push(...regularFiles(candidate));
    if (entry.isFile()) files.push(candidate);
  }
  return files;
}

function run(command, args, options) {
  const result = spawnSync(command, args, {
    ...options,
    encoding: "utf8",
    timeout: 30000,
    shell: process.platform === "win32"
  });
  assert.equal(result.error, undefined, result.error?.message);
  return result;
}

test("packed CLI has exact inventory and an isolated lifecycle", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-pack-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const artifacts = path.join(sandbox, "artifacts");
  const prefix = path.join(sandbox, "prefix");
  const cache = path.join(sandbox, "cache");
  const home = path.join(sandbox, "home");
  const project = path.join(sandbox, "project");
  for (const directory of [artifacts, prefix, cache, home, project]) {
    mkdirSync(directory, { recursive: true });
  }
  const env = {
    ...process.env,
    HOME: home,
    USERPROFILE: home,
    npm_config_cache: cache,
    npm_config_update_notifier: "false"
  };

  const externalTarball = process.env.DEEPER_READING_TARBALL;
  const packArgs = externalTarball
    ? ["pack", "--dry-run", "--json"]
    : ["pack", "--json", "--pack-destination", artifacts];
  const packed = run(npmCommand(), packArgs, { cwd: ROOT, env });
  assert.equal(packed.status, 0, packed.stderr);
  const metadata = parseJson(packed.stdout)[0];
  const manifest = loadManifest(path.join(ROOT, "MANIFEST.json"));
  const expected = new Set(
    payloadFiles(ROOT, manifest).map((file) => portable(path.relative(ROOT, file)))
  );
  for (const file of ["package.json", "MANIFEST.json", "LICENSE"]) {
    expected.add(file);
  }
  for (const file of regularFiles(path.join(ROOT, "installer", "node"))) {
    expected.add(portable(path.relative(ROOT, file)));
  }
  const actual = metadata.files.map(({ path: file }) => portable(file)).sort();
  assert.deepEqual(actual, [...expected].sort());

  const tarball = externalTarball
    ? path.resolve(externalTarball)
    : path.join(artifacts, metadata.filename);
  assert.equal(existsSync(tarball), true, tarball);
  const installed = run(npmCommand(), [
    "install", "--global", "--prefix", prefix, tarball,
    "--ignore-scripts", "--no-audit", "--no-fund"
  ], { cwd: project, env });
  assert.equal(installed.status, 0, installed.stderr);

  const executable = process.platform === "win32"
    ? path.join(prefix, "deeper-reading.cmd")
    : path.join(prefix, "bin", "deeper-reading");
  assert.equal(existsSync(executable), true, executable);
  const common = [
    "--target", "generic-agents", "--scope", "project",
    "--project-dir", project, "--json"
  ];
  const invoke = (args) => run(executable, args, { cwd: project, env });
  const target = path.join(project, ".agents", "skills", "deeper-reading");
  const userTarget = path.join(home, ".agents", "skills", "deeper-reading");

  const doctor = invoke(["doctor", ...common]);
  assert.equal(doctor.status, 0, doctor.stderr);
  assert.equal(parseJson(doctor.stdout).mutation_performed, false);
  const dryRun = invoke(["install", ...common, "--dry-run"]);
  assert.equal(dryRun.status, 0, dryRun.stderr);
  assert.equal(parseJson(dryRun.stdout).state, "dry-run");
  assert.equal(existsSync(target), false);
  const install = invoke(["install", ...common]);
  assert.equal(install.status, 0, install.stderr);
  assert.equal(existsSync(path.join(target, "SKILL.md")), true);
  const verify = invoke(["verify", ...common]);
  assert.equal(verify.status, 0, verify.stderr);
  assert.equal(parseJson(verify.stdout).passed, true);
  const uninstall = invoke(["uninstall", ...common]);
  assert.equal(uninstall.status, 0, uninstall.stderr);
  assert.equal(existsSync(path.join(target, "SKILL.md")), false);
  assert.equal(existsSync(userTarget), false);

  const npxDoctor = run(npxCommand(), [
    "--yes", "--package", tarball, "deeper-reading", "doctor", ...common
  ], { cwd: project, env });
  assert.equal(npxDoctor.status, 0, npxDoctor.stderr);
  assert.equal(parseJson(npxDoctor.stdout).mutation_performed, false);
  assert.equal(existsSync(userTarget), false);
});
