import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { SKILL_ROOT } from "./helpers.js";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pkg = JSON.parse(readFileSync(path.join(ROOT, "package.json"), "utf8"));
const version = readFileSync(path.join(SKILL_ROOT, "VERSION"), "utf8").trim();

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
  physicalPath,
  skillRoot,
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
  assert.ok(hashes["LICENSE"], "LICENSE ships so both installers copy the MIT notice");
  assert.ok(files.some((file) => path.basename(file) === "LICENSE"));
  assert.equal(Object.keys(hashes).some((name) => name.includes("\\")), false);
});

function rootedPackage(t, root) {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-skillroot-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const pkg = path.join(sandbox, "pkg");
  const skill = path.join(pkg, "skills", "demo");
  mkdirSync(path.join(skill, "modules"), { recursive: true });
  writeFileSync(path.join(skill, "SKILL.md"), "---\nname: demo\n---\nbody\n", "utf8");
  writeFileSync(path.join(skill, "modules", "a.txt"), "a", "utf8");
  const manifest = {
    skill: { name: "demo", entrypoint: "SKILL.md", ...(root === undefined ? {} : { root }) },
    payload: ["SKILL.md", "modules"],
    document_profiles: { standalone: {}, "oai-native": {} }
  };
  return { sandbox, pkg, manifest };
}

test("skill.root points the payload at the skill folder", (t) => {
  const { pkg, manifest } = rootedPackage(t, "skills/demo");
  assert.deepEqual(validateManifest(manifest, pkg), []);
  assert.deepEqual(Object.keys(payloadHashes(pkg, manifest)), ["modules/a.txt", "SKILL.md"]);
  const demo = path.join(pkg, "skills", "demo");
  assert.ok(payloadFiles(pkg, manifest).every((file) => file.startsWith(demo + path.sep)));
  assert.equal(skillRoot(manifest, pkg), physicalPath(path.join(pkg, "skills", "demo")));
});

test("a payload without modules is refused", (t) => {
  const { pkg, manifest } = rootedPackage(t, "skills/demo");
  const bare = { ...manifest, payload: ["SKILL.md"] };
  assert.deepEqual(validateManifest(bare, pkg), ["Standalone runtime payload must include package-owned modules"]);
});

test("skill.root of '.' validates the same as no field", (t) => {
  const { pkg, manifest } = rootedPackage(t, undefined);
  writeFileSync(path.join(pkg, "SKILL.md"), "---\nname: demo\n---\n", "utf8");
  mkdirSync(path.join(pkg, "modules"), { recursive: true });
  const dot = { ...manifest, skill: { ...manifest.skill, root: "." } };
  assert.deepEqual(validateManifest(manifest, pkg), []);
  assert.deepEqual(validateManifest(dot, pkg), []);
  assert.equal(skillRoot(dot, pkg), skillRoot(manifest, pkg));
});

const BAD_ROOTS = [
  [5, "skill.root must be a string"],
  [null, "skill.root must be a string"],
  ["/abs/skills", "skill.root must be a relative path"],
  ["", "skill.root must be a relative path"],
  ["skills\\demo", "skill.root must be a relative path"],
  ["C:skills", "skill.root must be a relative path"],
  ["skills/../skills/demo", "skill.root must not contain .."]
];

for (const root of ["skills/none", "skills/demo/SKILL.md", "skills/demo/SKILL.md/sub"]) {
  test(`skill.root ${JSON.stringify(root)} without a SKILL.md reports the missing entrypoint`, (t) => {
    const { pkg, manifest } = rootedPackage(t, root);
    const errors = validateManifest(manifest, pkg);
    assert.deepEqual(errors, ["Missing canonical SKILL.md at package root"]);
  });
}

for (const [root, expected] of BAD_ROOTS) {
  test(`skill.root ${JSON.stringify(root)} is refused with one error`, (t) => {
    const { pkg, manifest } = rootedPackage(t, root);
    assert.deepEqual(validateManifest(manifest, pkg), [expected]);
  });
}

test("skill.root that is absolute and has no SKILL.md reports only the first rule", (t) => {
  const { pkg, manifest } = rootedPackage(t, path.join(os.tmpdir(), "dr-no-such-root"));
  assert.deepEqual(validateManifest(manifest, pkg), ["skill.root must be a relative path"]);
});

test("skill.root that resolves outside the package through a link is refused", (t) => {
  const { sandbox, pkg, manifest } = rootedPackage(t, "escape");
  const outside = path.join(sandbox, "outside");
  mkdirSync(outside);
  writeFileSync(path.join(outside, "SKILL.md"), "---\nname: demo\n---\n", "utf8");
  try {
    symlinkSync(outside, path.join(pkg, "escape"), process.platform === "win32" ? "junction" : "dir");
  } catch (error) {
    if (["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) return t.skip("links unavailable");
    throw error;
  }
  assert.deepEqual(validateManifest(manifest, pkg), ["skill.root is outside the package root"]);
});

for (const root of ["loop", "loop/sub"]) {
  test(`skill.root ${JSON.stringify(root)} through a symlink loop gives one error`, (t) => {
    const { pkg, manifest } = rootedPackage(t, root);
    try {
      symlinkSync("loop", path.join(pkg, "loop"), process.platform === "win32" ? "junction" : "dir");
    } catch (error) {
      if (["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) return t.skip("links unavailable");
      throw error;
    }
    const errors = validateManifest(manifest, pkg);
    assert.equal(errors.length, 1, errors.join("; "));
    assert.match(errors[0], /^too many symbolic links/);
  });
}

test("managedPath rejects lexical and symlink escapes", (t) => {
  const sandbox = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-paths-"));
  t.after(() => rmSync(sandbox, { recursive: true, force: true }));
  const root = path.join(sandbox, "root");
  const outside = path.join(sandbox, "outside");
  mkdirSync(root);
  mkdirSync(outside);
  writeFileSync(path.join(outside, "victim.txt"), "keep", "utf8");
  // Absolute spellings are built from the tmp victim so they never name a real location.
  const victim = path.join(outside, "victim.txt");
  const spellings = [
    victim,
    `\\\\?\\${victim}`,
    victim.replaceAll("\\", "/"),
    "../outside.txt",
    "C:foo",
    "Z:/dr-no-such/x",
    "//dr-no-such-host/share/x"
  ];
  for (const raw of spellings) assert.throws(() => managedPath(root, raw), InstallerError, raw);
  try {
    const link = path.join(root, "escape");
    const type = process.platform === "win32" ? "junction" : "dir";
    symlinkSync(outside, link, type);
    assert.throws(() => managedPath(root, "escape/victim.txt"), InstallerError);
  } catch (error) {
    if (!["EPERM", "EACCES", "ENOTSUP"].includes(error.code)) throw error;
  }
});
