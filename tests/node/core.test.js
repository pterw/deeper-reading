import assert from "node:assert/strict";
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  symlinkSync,
  writeFileSync
} from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { loadManifest, sha256File } from "../../installer/node/manifest.js";
import {
  buildInstallPlan,
  installSkill,
  uninstallSkill,
  verifyInstallation
} from "../../installer/node/core.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const READY = { state: "ready", evidence: ["test-ready"], action: [] };

function fixture(t) {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-core-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const targetRoot = path.join(sandbox, "skills", "deeper-reading");
  const options = {
    packageRoot: ROOT,
    targetRoot,
    manifest: loadManifest(path.join(ROOT, "MANIFEST.json")),
    targetName: "generic-agents",
    scope: "user",
    runtimeProfile: "standalone",
    documentProfile: "standalone",
    documentStatus: READY,
    discoveryVerifier: null
  };
  return { sandbox, targetRoot, options };
}

function readReceipt(targetRoot) {
  return JSON.parse(readFileSync(path.join(targetRoot, ".install-receipt.json"), "utf8"));
}

function writeReceipt(targetRoot, receipt) {
  writeFileSync(
    path.join(targetRoot, ".install-receipt.json"),
    `${JSON.stringify(receipt, null, 2)}\n`,
    "utf8"
  );
}

test("fresh install writes canonical payload and compatible receipt", (t) => {
  const { targetRoot, options } = fixture(t);
  const result = installSkill(options);
  const receipt = JSON.parse(readFileSync(path.join(targetRoot, ".install-receipt.json"), "utf8"));
  assert.equal(result.state, "installed");
  assert.equal(existsSync(path.join(targetRoot, "SKILL.md")), true);
  assert.deepEqual(Object.keys(receipt).sort(), [
    "document_profile", "document_status", "host_discovery", "installed_at",
    "installed_root", "payload_hashes", "runtime_profile", "scope", "skill",
    "target", "version"
  ]);
  assert.equal(verifyInstallation(targetRoot).passed, true);
});

test("upgrade preserves unowned files and rejects modified managed files", (t) => {
  const { targetRoot, options } = fixture(t);
  installSkill(options);
  const note = path.join(targetRoot, "user-note.txt");
  writeFileSync(note, "mine", "utf8");
  installSkill(options);
  assert.equal(readFileSync(note, "utf8"), "mine");
  writeFileSync(path.join(targetRoot, "SKILL.md"), "changed", "utf8");
  assert.throws(() => installSkill(options), /modified managed files/);
});

test("uninstall refuses modified ownership unless forced and preserves unowned files", (t) => {
  const { targetRoot, options } = fixture(t);
  installSkill(options);
  const note = path.join(targetRoot, "user-note.txt");
  writeFileSync(note, "mine", "utf8");
  writeFileSync(path.join(targetRoot, "SKILL.md"), "changed", "utf8");
  assert.throws(() => uninstallSkill(targetRoot), /modified owned files/);
  const result = uninstallSkill(targetRoot, { force: true });
  assert.equal(result.state, "uninstalled");
  assert.equal(readFileSync(note, "utf8"), "mine");
});

test("dry-run returns the shared plan without creating the target", (t) => {
  const { targetRoot, options } = fixture(t);
  const direct = buildInstallPlan(options);
  const result = installSkill({ ...options, dryRun: true });
  assert.deepEqual(result, direct);
  assert.equal(result.state, "dry-run");
  assert.equal(existsSync(targetRoot), false);
});

test("install refuses an existing root without a receipt", (t) => {
  const { targetRoot, options } = fixture(t);
  mkdirSync(targetRoot, { recursive: true });
  writeFileSync(path.join(targetRoot, "SKILL.md"), "unmanaged", "utf8");
  assert.throws(() => installSkill(options), /existing target is unmanaged/);
  assert.equal(readFileSync(path.join(targetRoot, "SKILL.md"), "utf8"), "unmanaged");
});

test("receipt path spellings outside the target are rejected before uninstall", (t) => {
  const malicious = [
    "/tmp/outside.txt", "../outside.txt", "C:/outside.txt", "C:foo",
    "C:\\outside.txt", "\\\\server\\share\\outside.txt"
  ];
  for (const raw of malicious) {
    const { targetRoot, options } = fixture(t);
    installSkill(options);
    const receipt = readReceipt(targetRoot);
    receipt.payload_hashes = { [raw]: "0".repeat(64) };
    writeReceipt(targetRoot, receipt);
    assert.throws(() => uninstallSkill(targetRoot), /managed payload path/);
    rmSync(targetRoot, { recursive: true, force: true });
  }
});

test("receipt symlink escapes are rejected without touching outside bytes", (t) => {
  const { sandbox, targetRoot, options } = fixture(t);
  installSkill(options);
  const outside = path.join(sandbox, "outside");
  const victim = path.join(outside, "victim.txt");
  mkdirSync(outside);
  writeFileSync(victim, "keep", "utf8");
  try {
    symlinkSync(outside, path.join(targetRoot, "escape"), process.platform === "win32" ? "junction" : "dir");
  } catch (error) {
    if (["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) return;
    throw error;
  }
  const receipt = readReceipt(targetRoot);
  receipt.payload_hashes = { "escape/victim.txt": sha256File(victim) };
  writeReceipt(targetRoot, receipt);
  assert.equal(verifyInstallation(targetRoot).passed, false);
  assert.throws(() => uninstallSkill(targetRoot), /managed payload path/);
  assert.equal(readFileSync(victim, "utf8"), "keep");
});

test("upgrade removes files owned only by the old manifest", (t) => {
  const { sandbox, targetRoot, options } = fixture(t);
  const packageRoot = path.join(sandbox, "package");
  cpSync(ROOT, packageRoot, {
    recursive: true,
    filter: (source) => ![".git", "node_modules", "__pycache__", ".pytest_cache"].includes(path.basename(source))
  });
  const manifestPath = path.join(packageRoot, "MANIFEST.json");
  const oldManifest = loadManifest(manifestPath);
  oldManifest.payload.push("legacy-managed.txt");
  writeFileSync(path.join(packageRoot, "legacy-managed.txt"), "legacy", "utf8");
  writeFileSync(manifestPath, `${JSON.stringify(oldManifest, null, 2)}\n`, "utf8");
  installSkill({ ...options, packageRoot, manifest: oldManifest });
  const nextManifest = loadManifest(manifestPath);
  nextManifest.payload = nextManifest.payload.filter((entry) => entry !== "legacy-managed.txt");
  writeFileSync(manifestPath, `${JSON.stringify(nextManifest, null, 2)}\n`, "utf8");
  installSkill({ ...options, packageRoot, manifest: nextManifest });
  assert.equal(existsSync(path.join(targetRoot, "legacy-managed.txt")), false);
});

test("successful install leaves no stage or backup siblings", (t) => {
  const { targetRoot, options } = fixture(t);
  installSkill(options);
  const siblings = new Set(readdirSync(path.dirname(targetRoot)));
  assert.equal([...siblings].some((name) => name.startsWith(".deeper-reading.stage-")), false);
  assert.equal([...siblings].some((name) => name.startsWith(".deeper-reading.backup-")), false);
});

test("failure after replacement restores the prior installation", (t) => {
  const { sandbox, targetRoot, options } = fixture(t);
  installSkill(options);
  const original = readFileSync(path.join(targetRoot, "SKILL.md"));
  const packageRoot = path.join(sandbox, "replacement-package");
  cpSync(ROOT, packageRoot, {
    recursive: true,
    filter: (source) => ![".git", "node_modules", "__pycache__", ".pytest_cache"].includes(path.basename(source))
  });
  writeFileSync(path.join(packageRoot, "README.md"), "replacement\n", "utf8");
  assert.throws(() => installSkill({
    ...options,
    packageRoot,
    manifest: loadManifest(path.join(packageRoot, "MANIFEST.json")),
    failureInjector(point) {
      if (point === "after-replace") throw new Error("injected after-replace failure");
    }
  }), /injected after-replace failure/);
  assert.deepEqual(readFileSync(path.join(targetRoot, "SKILL.md")), original);
  assert.equal(verifyInstallation(targetRoot).passed, true);
});

test("verify reports payload hash mismatch", (t) => {
  const { targetRoot, options } = fixture(t);
  installSkill(options);
  writeFileSync(path.join(targetRoot, "SKILL.md"), "changed", "utf8");
  const result = verifyInstallation(targetRoot);
  assert.equal(result.passed, false);
  assert.equal(result.predicates.payload_hashes_match, false);
});

test("verify rejects a receipt for a different installed root", (t) => {
  const { sandbox, targetRoot, options } = fixture(t);
  installSkill(options);
  const receipt = readReceipt(targetRoot);
  receipt.installed_root = path.join(sandbox, "elsewhere", "deeper-reading");
  writeReceipt(targetRoot, receipt);
  const result = verifyInstallation(targetRoot);
  assert.equal(result.passed, false);
  assert.equal(result.predicates.receipt_matches_installed_root, false);
});
