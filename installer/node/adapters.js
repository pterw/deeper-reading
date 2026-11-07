import { accessSync, constants, statSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { discoveryState } from "./discovery.js";

export const TARGET_NAMES = ["auto", "generic-agents", "copilot", "codex", "gemini", "claude"];
const SKILL_NAME = "deeper-reading";
const ROOTS = {
  "generic-agents": [".agents", ".agents"],
  copilot: [".copilot", ".github"],
  codex: [".agents", ".agents"],
  gemini: [".gemini", ".gemini"],
  claude: [".claude", ".claude"]
};

const LAUNCHABLE = [".com", ".exe", ".bat", ".cmd"];
const TRAILING_DOTS = /(?<=[^./\\:])\.+(?=[/\\]|$)/g;
const CURRENT_DIRECTORY = /^(?:\.(?:\/+\.?)*)?$/;
const CURRENT_DIRECTORY_WIN32 = /^(?:\.(?:[/\\]+\.?)*)?$/;
const UNSAFE_SHIM_CHARACTERS = new Set(['"', "%", "&", "|", "<", ">", "^", "!", "(", ")", ",", ";", "=", "\r", "\n"]);

function isFile(candidate) {
  try {
    return statSync(candidate).isFile();
  } catch {
    return false;
  }
}

function isExecutableFile(candidate) {
  try {
    accessSync(candidate, constants.X_OK);
  } catch {
    return false;
  }
  return isFile(candidate);
}

// Rule R29, identical in installer/adapters/base.py (shared table:
// tests/fixtures/host-resolution-cases.json): only PATH entries are searched, never the current
// directory; entries and PATHEXT members are trimmed and unquoted; empty and current-directory
// entries (".", "./", ".\.") are skipped; Win32 drops the trailing dots of every path segment. On win32 the extensions are
// the PATHEXT members cmd.exe can launch, in PATHEXT order.
function normalise(value) {
  const trimmed = value.trim();
  return trimmed.length > 1 && trimmed.startsWith('"') && trimmed.endsWith('"') ? trimmed.slice(1, -1) : trimmed;
}

export function resolveCommand(command, { env = process.env, platform = process.platform } = {}) {
  const win32 = platform === "win32";
  const extensions = win32
    ? (env.PATHEXT || ".COM;.EXE;.BAT;.CMD").split(";")
      .map((extension) => normalise(extension).toLowerCase())
      .filter((extension) => LAUNCHABLE.includes(extension))
    : [""];
  for (const entry of (env.PATH ?? env.Path ?? "").split(win32 ? ";" : path.delimiter)) {
    const normalised = normalise(entry);
    const directory = win32 ? normalised.replace(TRAILING_DOTS, "") : normalised;
    if ((win32 ? CURRENT_DIRECTORY_WIN32 : CURRENT_DIRECTORY).test(directory)) continue;
    for (const extension of extensions) {
      const candidate = path.join(path.resolve(directory), command + extension);
      if (win32 ? isFile(candidate) : isExecutableFile(candidate)) return candidate;
    }
  }
  return null;
}

export function commandExists(command, options = {}) {
  return resolveCommand(command, options) !== null;
}

// Frozen refusal set F2 for a resolved .cmd/.bat path: returns the first offending
// character, or null. Pure; the caller decides which paths it applies to.
export function unsafeShimPath(shimPath) {
  for (const character of shimPath) if (UNSAFE_SHIM_CHARACTERS.has(character)) return character;
  return null;
}

// The refusal applies to a resolved .cmd/.bat path on win32 only; first offending character or null.
export function hostPathRefusal(resolved, platform = process.platform) {
  return platform === "win32" && /\.(cmd|bat)$/i.test(resolved) ? unsafeShimPath(resolved) : null;
}

// Frozen rule F2. Safe ONLY for a constant argument vector: on win32 a .cmd/.bat shim must go
// through cmd.exe (spawnSync of a .cmd fails with EINVAL), and the command line below is built
// by string concatenation, which is injection-free only because `args` never holds variable
// parts and the shim path has passed unsafeShimPath.
function launchHost(resolved, args, { env, platform }) {
  const spawnOptions = { encoding: "utf8", timeout: 30000, env };
  if (platform !== "win32" || !/\.(cmd|bat)$/i.test(resolved)) return spawnSync(resolved, args, spawnOptions);
  const comspec = env.ComSpec || path.join(env.SystemRoot || "C:\\Windows", "System32", "cmd.exe");
  return spawnSync(comspec, ["/d", "/v:off", "/s", "/c", `""${resolved}" ${args.join(" ")}"`],
    { ...spawnOptions, windowsVerbatimArguments: true });
}

export function detectTarget(options = {}) {
  for (const name of ["copilot", "gemini", "codex", "claude"])
    if (commandExists(name, options)) return name;
  return "generic-agents";
}

export function getAdapter(name, options = {}) {
  if (!Object.hasOwn(ROOTS, name)) throw new Error(`unsupported target: ${name}`);
  const [userBase, projectBase] = ROOTS[name];
  const homeDir = options.homeDir || os.homedir();
  return {
    name,
    detect: () => name === "generic-agents" || commandExists(name, options),
    resolveSkillRoot(scope, projectDir) {
      if (scope === "user") return path.resolve(homeDir, userBase, "skills", SKILL_NAME);
      if (scope !== "project") throw new Error(`unsupported scope: ${scope}`);
      if (!projectDir) throw new Error("project scope requires --project-dir");
      return path.resolve(projectDir, projectBase, "skills", SKILL_NAME);
    },
    discoveryVerify(skillName) {
      const args = name === "copilot" ? ["skill", "list", "--json"]
        : name === "gemini" ? ["skills", "list"] : null;
      const resolved = args ? resolveCommand(name, options) : null;
      if (!resolved)
        return { state: "not-available", evidence: [`${name} has no available stable discovery command`] };
      const env = options.env || process.env;
      const platform = options.platform || process.platform;
      const unsafe = hostPathRefusal(resolved, platform);
      if (unsafe !== null)
        return { state: "failed", evidence: [`unsafe host command path: ${resolved} (character ${unsafe})`] };
      let result;
      try {
        result = launchHost(resolved, args, { env, platform });
      } catch (error) {
        return { state: "failed", evidence: [`${error.code || error.name}: ${error.message}`] };
      }
      const stdout = result.stdout == null ? "" : String(result.stdout);
      const stderr = result.stderr == null ? "" : String(result.stderr);
      const evidence = [`exit=${result.status}`, stdout.trim(), stderr.trim()];
      if (result.error) evidence.push(`${result.error.code || result.error.name}: ${result.error.message}`);
      if (result.signal) evidence.push(`signal=${result.signal}`);
      if (result.error || result.signal || result.status !== 0) return { state: "failed", evidence };
      const state = discoveryState(name, stdout, skillName);
      if (state === "failed") evidence.push(`unrecognized ${name} ${args.join(" ")} output`);
      return { state, evidence };
    }
  };
}
