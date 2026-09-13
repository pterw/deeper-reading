import { existsSync } from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export const BUNDLED_EXTRACTORS = [
  "extract_pdf.py",
  "extract_docx.py",
  "extract_html.py",
  "extract_markdown.py"
];

const VERSION_PROBE = "import sys; print('.'.join(map(str, sys.version_info[:3])))";
const PYTHON_ACTION = [
  "Install a supported Python 3.10-3.13 runtime before running the installed extraction or verification scripts."
];
const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function status(state, evidence = [], action = []) {
  return { state, evidence, action };
}

export function documentProfileStatus(profile, options = {}) {
  const normalized = profile.toLowerCase();
  const packageRoot = path.resolve(options.packageRoot || PACKAGE_ROOT);
  if (normalized === "standalone") {
    const required = BUNDLED_EXTRACTORS.map((name) => path.join(packageRoot, "scripts", name));
    const missing = required.filter((candidate) => !existsSync(candidate));
    return missing.length
      ? status(
          "missing",
          missing.map((candidate) => `missing:${candidate}`),
          ["Restore the bundled extraction payload before installation."]
        )
      : status("ready", required.map((candidate) => `bundled=${candidate}`));
  }
  if (normalized === "oai-native") {
    const pdf = path.resolve(options.nativePdf || "/home/oai/skills/pdfs");
    const docx = path.resolve(options.nativeDocx || "/home/oai/skills/docx");
    const missing = [pdf, docx].filter((candidate) => !existsSync(path.join(candidate, "SKILL.md")));
    return missing.length
      ? status(
          "missing",
          missing.map((candidate) => `missing:${candidate}`),
          ["Use the standalone profile or run inside an OAI-native harness."]
        )
      : status("ready", [
          `pdf=${pdf}`,
          `docx=${docx}`,
          "enhancement=oai-native-does-not-alter-anti-skimming-contract"
        ]);
  }
  return status("unsupported", [`unknown document profile: ${normalized}`]);
}

export function pythonRuntimeStatus(options = {}) {
  const spawn = options.spawn || spawnSync;
  const candidates = options.candidates || (process.platform === "win32"
    ? [["py", ["-3"]], ["python", []], ["python3", []]]
    : [["python3", []], ["python", []]]);
  const evidence = [];
  for (const [command, prefix] of candidates) {
    const result = spawn(command, [...prefix, "-c", VERSION_PROBE], {
      encoding: "utf8",
      timeout: 30000,
      env: options.env || process.env
    });
    if (result.error) {
      evidence.push(`${command}: ${result.error.code || result.error.message}`);
      continue;
    }
    const version = result.stdout.trim();
    evidence.push(`${command}: exit=${result.status} version=${version || "unknown"}`);
    if (result.status !== 0) continue;
    const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(version);
    if (match && Number(match[1]) === 3 && Number(match[2]) >= 10 && Number(match[2]) <= 13) {
      return status("ready", evidence);
    }
  }
  return status("blocked", evidence, PYTHON_ACTION);
}
