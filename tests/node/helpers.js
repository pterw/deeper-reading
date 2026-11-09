import { spawnSync } from "node:child_process";
import { mkdirSync, symlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const LINK_TYPE = process.platform === "win32" ? "junction" : "dir";

// Builds `a0/b0/escape` under base: two chains of `count` links, so a path through both follows more
// than the 40 links Linux allows, ending at a link to `outside`. Returns that relative path.
export function linkChainEscape(base, outside, count = 25) {
  const chain = (prefix, target) => {
    symlinkSync(target, path.join(base, `${prefix}${count}`), LINK_TYPE);
    for (let i = count - 1; i >= 0; i -= 1) symlinkSync(path.join(base, `${prefix}${i + 1}`), path.join(base, `${prefix}${i}`), LINK_TYPE);
  };
  mkdirSync(path.join(base, "reala"));
  mkdirSync(path.join(base, "realb"));
  chain("a", path.join(base, "reala"));
  chain("b", path.join(base, "realb"));
  symlinkSync(path.join(base, "b0"), path.join(base, "reala", "b0"), LINK_TYPE);
  symlinkSync(outside, path.join(base, "realb", "escape"), LINK_TYPE);
  return "a0/b0/escape";
}

// Builds `X0/L/last` under base with exactly 40 links before the last component: X0..X39 lead to R,
// R/L leads to R2 (the 41st link), R2/last leads to `outside`. A lookup of the whole path fails with
// ELOOP on Linux while a lookup of `X0/L` does not. Returns that relative path.
export function fortyLinkEscape(base, outside) {
  mkdirSync(path.join(base, "R"));
  mkdirSync(path.join(base, "R2"));
  symlinkSync(path.join(base, "R2"), path.join(base, "R", "L"), LINK_TYPE);
  symlinkSync(outside, path.join(base, "R2", "last"), LINK_TYPE);
  symlinkSync(path.join(base, "R"), path.join(base, "X39"), LINK_TYPE);
  for (let i = 38; i >= 0; i -= 1) symlinkSync(path.join(base, `X${i + 1}`), path.join(base, `X${i}`), LINK_TYPE);
  return "X0/L/last";
}

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const SKILL_ROOT = path.join(ROOT, "skills", "deeper-reading");

export function npmCommand() {
  return process.platform === "win32" ? "npm.cmd" : "npm";
}

export function npxCommand() {
  return process.platform === "win32" ? "npx.cmd" : "npx";
}

export function findPython() {
  const candidates = process.platform === "win32"
    ? [["py", ["-3"]], ["python", []], ["python3", []]]
    : [["python3", []], ["python", []]];
  for (const [command, prefix] of candidates) {
    const result = spawnSync(command, [...prefix, "-c", "import sys; print(sys.executable)"], {
      encoding: "utf8",
      timeout: 30000
    });
    if (result.status === 0) return { command, prefix };
  }
  throw new Error("supported Python command not found for parity test");
}

function subprocessEnv({ home, env = {} } = {}) {
  const value = { ...process.env, ...env };
  if (home) {
    value.HOME = home;
    value.USERPROFILE = home;
  }
  return value;
}

export function runNodeCli(args, options = {}) {
  return spawnSync(process.execPath, [path.join(ROOT, "installer", "node", "cli.js"), ...args], {
    cwd: options.cwd || ROOT,
    env: subprocessEnv(options),
    encoding: "utf8",
    timeout: 30000
  });
}

export function runPythonCli(args, options = {}) {
  const { command, prefix } = findPython();
  return spawnSync(command, [...prefix, path.join(ROOT, "installer", "install.py"), ...args], {
    cwd: options.cwd || ROOT,
    env: subprocessEnv(options),
    encoding: "utf8",
    timeout: 30000
  });
}

export function parseJson(stdout) {
  assertNonEmpty(stdout);
  return JSON.parse(stdout);
}

function assertNonEmpty(stdout) {
  if (!stdout.trim()) throw new Error("subprocess produced no JSON stdout");
}
