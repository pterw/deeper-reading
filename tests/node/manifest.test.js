import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pkg = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf8"));
const version = readFileSync(path.join(ROOT, "VERSION"), "utf8").trim();

test("npm metadata exposes the explicit CLI and matches VERSION", () => {
  assert.equal(pkg.name, "deeper-reading");
  assert.equal(pkg.version, version);
  assert.deepEqual(pkg.bin, { "deeper-reading": "installer/node/cli.js" });
  assert.equal(pkg.type, "module");
  assert.equal(pkg.engines.node, ">=20");
});

test("npm metadata has no mutation lifecycle", () => {
  const forbidden = [
    "preinstall", "install", "postinstall", "prepare", "prepack", "postpack"
  ];
  for (const name of forbidden) {
    assert.equal(pkg.scripts?.[name], undefined, name);
  }
  assert.deepEqual(pkg.dependencies ?? {}, {});
  assert.deepEqual(pkg.devDependencies ?? {}, {});
});

import {
  mkdtempSync,
  mkdirSync,
  rmSync,
  symlinkSync,
  writeFileSync
} from "node:fs";
import os from "node:os";
import {
  InstallerError,
  loadManifest,
  managedPath,
  payloadFiles,
  payloadHashes,
  validateManifest
} from "../../installer/node/manifest.js";

test("manifest validates the canonical package and enumerates forward-slash paths", () => {
  const manifest = loadManifest(path.join(ROOT, "MANIFEST.json"));
  assert.deepEqual(validateManifest(manifest, ROOT), []);
  const files = payloadFiles(ROOT, manifest);
  assert.ok(files.some((file) => file.endsWith(path.join("scripts", "verify_run.py"))));
  const hashes = payloadHashes(ROOT, manifest);
  assert.ok(hashes["SKILL.md"]);
  assert.ok(hashes["scripts/verify_run.py"]);
  assert.equal(Object.keys(hashes).some((name) => name.includes("\\")), false);
});

test("managedPath rejects lexical and symlink escapes", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-paths-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const root = path.join(sandbox, "root");
  const outside = path.join(sandbox, "outside");
  mkdirSync(root);
  mkdirSync(outside);
  writeFileSync(path.join(outside, "victim.txt"), "keep", "utf8");
  for (const raw of ["/tmp/x", "../x", "C:/x", "C:\\x", "\\\\server\\share\\x"])
    assert.throws(() => managedPath(root, raw), InstallerError);
  try {
    const link = path.join(root, "escape");
    const type = process.platform === "win32" ? "junction" : "dir";
    symlinkSync(outside, link, type);
    assert.throws(() => managedPath(root, "escape/victim.txt"), InstallerError);
  } catch (error) {
    if (!["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) throw error;
  }
});
