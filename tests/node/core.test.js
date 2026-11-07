import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import {
  chmodSync,
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
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
import { runNodeCli } from "./helpers.js";

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

test("drive and UNC receipt spellings are rejected on every OS", (t) => {
  for (const raw of ["Z:/dr-no-such/x", "//dr-no-such-host/share/x"]) {
    const { targetRoot, options } = fixture(t);
    installSkill(options);
    const receipt = readReceipt(targetRoot);
    receipt.payload_hashes = { [raw]: "0".repeat(64) };
    writeReceipt(targetRoot, receipt);
    assert.throws(() => uninstallSkill(targetRoot, { force: true }), /managed payload path/);
  }
});

test("receipt path spellings outside the target are rejected without touching the victim", (t) => {
  // Every spelling resolves to the victim inside the sandbox (or stays relative
  // and harmless), so a containment regression deletes a tmp file, never a real one.
  const spellings = [
    (victim) => victim,
    (victim) => `\\\\?\\${victim}`,
    () => "../outside.txt",
    () => "C:foo",
    ...(path.sep === "/" ? [] : [(victim) => victim.replaceAll("\\", "/")])
  ];
  for (const spell of spellings) {
    const { sandbox, targetRoot, options } = fixture(t);
    installSkill(options);
    const victim = path.join(sandbox, "outside.txt");
    writeFileSync(victim, "do not touch", "utf8");
    const raw = spell(victim);
    const receipt = readReceipt(targetRoot);
    receipt.payload_hashes = { [raw]: sha256File(victim) };
    writeReceipt(targetRoot, receipt);
    assert.throws(() => uninstallSkill(targetRoot, { force: true }), /managed payload path/, raw);
    assert.equal(readFileSync(victim, "utf8"), "do not touch", raw);
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

function sleepSync(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function isAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch {
    return false;
  }
}

// Makes the real backup removal fail: a child process holding a directory inside
// the backup on Windows, a read-only directory elsewhere. Returns an undo function.
function makeBackupUndeletable(targetRoot) {
  const parent = path.dirname(targetRoot);
  const name = readdirSync(parent).find((entry) => entry.includes(".backup-"));
  const locked = path.join(parent, name, "references");
  if (process.platform === "win32") {
    // The child takes its working directory only once it has started, so wait for it.
    const ready = path.join(path.dirname(parent), "child-ready");
    const script = `require("fs").writeFileSync(${JSON.stringify(ready)}, "1"); setInterval(() => {}, 1000)`;
    const child = spawn(process.execPath, ["-e", script], { cwd: locked, stdio: "ignore" });
    const deadline = Date.now() + 10000;
    while (!existsSync(ready) && Date.now() < deadline) {
      sleepSync(50);
    }
    return () => {
      child.kill();
      const gone = Date.now() + 10000;
      while (Date.now() < gone && isAlive(child.pid)) {
        sleepSync(50);
      }
      sleepSync(300); // Windows releases the directory handle a moment after exit
    };
  }
  chmodSync(locked, 0o500);
  return () => chmodSync(locked, 0o700);
}

for (const mode of ["injector", "real-removal"]) {
  test(`backup cleanup failure after the commit point keeps the new install and warns (${mode})`, (t) => {
    if (mode === "real-removal" && process.platform !== "win32" && process.getuid?.() === 0) {
      t.skip("root ignores directory permissions");
      return;
    }
    const { targetRoot, options } = fixture(t);
    assert.equal("warnings" in installSkill(options), false);
    let undo = () => {};
    let result;
    try {
      result = installSkill({
        ...options,
        failureInjector(point) {
          if (mode === "injector" && point === "cleanup-backup") {
            throw new Error("injected cleanup failure");
          }
          if (mode === "real-removal" && point === "after-receipt") {
            undo = makeBackupUndeletable(targetRoot);
          }
        }
      });
      assert.equal(result.state, "installed");
      assert.equal(result.warnings.length, 1);
      assert.match(result.warnings[0], /backup cleanup failed/);
      assert.equal(existsSync(path.join(targetRoot, "SKILL.md")), true);
      const verdict = verifyInstallation(targetRoot);
      const failed = Object.keys(verdict.predicates).filter((name) => !verdict.predicates[name]);
      assert.deepEqual(failed, ["no_backup_leftovers"]);
    } finally {
      undo();
    }
  });
}

test("failure after the receipt still restores the prior installation", (t) => {
  const { targetRoot, options } = fixture(t);
  installSkill(options);
  const original = readFileSync(path.join(targetRoot, "SKILL.md"));
  assert.throws(() => installSkill({
    ...options,
    failureInjector(point) {
      if (point === "after-receipt") throw new Error("injected after-receipt failure");
    }
  }), /injected after-receipt failure/);
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

const CORRUPT_RECEIPTS = [
  ["truncated json", "{"],
  ["array", "[]"],
  ["null", "null"],
  ["string", "\"x\""],
  ["document_status int", "{\"document_status\": 3}"],
  ["payload_hashes array", "{\"payload_hashes\": [\"a\"]}"],
  ["host_discovery string", "{\"host_discovery\": \"verified\"}"],
  ["document_status null", "{\"document_status\": null}"],
  ["host_discovery null", "{\"host_discovery\": null}"],
  ["unreadable, receipt is a directory", null]
];

for (const [name, text] of CORRUPT_RECEIPTS) {
  test(`corrupt receipt (${name}) fails closed in install, verify and uninstall`, (t) => {
    const { targetRoot, options } = fixture(t);
    installSkill(options);
    const receiptPath = path.join(targetRoot, ".install-receipt.json");
    if (text === null) {
      rmSync(receiptPath);
      mkdirSync(receiptPath);
    } else {
      writeFileSync(receiptPath, text, "utf8");
    }
    assert.throws(() => installSkill(options), /invalid installation receipt/);
    const result = verifyInstallation(targetRoot);
    assert.equal(result.passed, false);
    assert.ok(result.violations.some((v) => v.includes("invalid installation receipt")));
    assert.throws(() => uninstallSkill(targetRoot, { force: true }), /invalid installation receipt/);
    assert.ok(existsSync(path.join(targetRoot, "SKILL.md")));
    if (text === null) {
      assert.ok(statSync(receiptPath).isDirectory());
    } else {
      assert.equal(readFileSync(receiptPath, "utf8"), text);
    }
  });
}

test("corrupt receipt through the CLI exits 2 with empty stderr and a structured error", (t) => {
  const { sandbox, options } = fixture(t);
  const home = path.join(sandbox, "home");
  const project = path.join(sandbox, "project");
  mkdirSync(home);
  mkdirSync(project);
  const targetRoot = path.join(project, ".agents", "skills", "deeper-reading");
  installSkill({ ...options, targetRoot, scope: "project" });
  writeFileSync(path.join(targetRoot, ".install-receipt.json"), "null", "utf8");
  for (const command of ["install", "verify", "uninstall"]) {
    const result = runNodeCli(
      [command, "--target", "generic-agents", "--scope", "project", "--project-dir", project, "--json"],
      { cwd: project, home }
    );
    assert.equal(result.status, 2, command);
    assert.equal(result.stderr, "", command);
    assert.match(result.stdout, /invalid installation receipt/);
  }
});
