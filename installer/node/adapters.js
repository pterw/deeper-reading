import { accessSync, constants } from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";

export const TARGET_NAMES = ["auto", "generic-agents", "copilot", "codex", "gemini", "claude"];
const SKILL_NAME = "deeper-reading";
const ROOTS = {
  "generic-agents": [".agents", ".agents"],
  copilot: [".copilot", ".github"],
  codex: [".agents", ".agents"],
  gemini: [".gemini", ".gemini"],
  claude: [".claude", ".claude"]
};

export function commandExists(command, { env = process.env, platform = process.platform } = {}) {
  const extensions = platform === "win32"
    ? (env.PATHEXT || ".COM;.EXE;.BAT;.CMD").split(";")
    : [""];
  for (const directory of (env.PATH || "").split(path.delimiter).filter(Boolean)) {
    for (const extension of extensions) {
      try {
        accessSync(path.join(directory, command + extension.toLowerCase()), constants.X_OK);
        return true;
      } catch {}
      try {
        accessSync(path.join(directory, command + extension.toUpperCase()), constants.X_OK);
        return true;
      } catch {}
    }
  }
  return false;
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
      const command = name === "copilot" ? ["copilot", "skill", "list"]
        : name === "gemini" ? ["gemini", "skills", "list"] : null;
      if (!command || !this.detect())
        return { state: "not-available", evidence: [`${name} has no available stable discovery command`] };
      const result = spawnSync(command[0], command.slice(1), { encoding: "utf8", timeout: 30000 });
      const evidence = [`exit=${result.status}`, result.stdout.trim(), result.stderr.trim()];
      if (result.status !== 0) return { state: "failed", evidence };
      return { state: result.stdout.includes(skillName) ? "verified" : "missing", evidence };
    }
  };
}
