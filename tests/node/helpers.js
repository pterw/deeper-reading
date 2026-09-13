import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

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
