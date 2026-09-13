#!/usr/bin/env node
import { existsSync, realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { TARGET_NAMES, detectTarget, getAdapter } from "./adapters.js";
import { documentProfileStatus, pythonRuntimeStatus } from "./prerequisites.js";
import { loadManifest, validateManifest } from "./manifest.js";
import { installSkill, uninstallSkill, verifyInstallation } from "./core.js";

const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const COMMANDS = new Set(["doctor", "install", "verify", "uninstall"]);
const COMMON_OPTIONS = new Set([
  "--target", "--scope", "--project-dir", "--document-profile", "--json"
]);
const COMMAND_OPTIONS = {
  doctor: new Set(),
  install: new Set(["--dry-run"]),
  uninstall: new Set(["--force"]),
  verify: new Set()
};
const SCOPES = new Set(["user", "project"]);
const DOCUMENT_PROFILES = new Set(["standalone", "oai-native"]);

class UsageError extends Error {}

const HELP_TEXT = `deeper-reading - install the manifest-owned skill payload

Usage:
  deeper-reading doctor  [options]
  deeper-reading install [options]
  deeper-reading verify  [options]
  deeper-reading uninstall [options]

Commands:
  doctor     Report target, package, document-profile, and Python runtime readiness.
  install    Install the manifest-owned payload transactionally.
  verify     Re-hash installed files and verify the receipt and runtime readiness.
  uninstall  Remove receipt-owned files.

Options:
  --target <name>            auto, generic-agents, copilot, codex, gemini, claude
  --scope <user|project>     default user
  --project-dir <path>       project root; defaults to the current directory
  --document-profile <name>  standalone or oai-native; default standalone
  --dry-run                  install only: compute the transaction without writing
  --force                    uninstall only: allow removing modified managed files
  --json                     emit one structured JSON value on stdout
  --help                     show this message`;

export function parseArgs(argv) {
  const tokens = [...argv];
  if (tokens.includes("--help")) {
    const candidate = tokens[0];
    return { help: true, command: COMMANDS.has(candidate) ? candidate : null };
  }
  if (tokens.length === 0) {
    throw new UsageError("missing command: expected doctor, install, verify, or uninstall");
  }
  const command = tokens.shift();
  if (!COMMANDS.has(command)) throw new UsageError(`unsupported command: ${command}`);
  const allowed = new Set([...COMMON_OPTIONS, ...COMMAND_OPTIONS[command]]);
  const options = {
    target: "auto",
    scope: "user",
    projectDir: null,
    documentProfile: "standalone",
    json: false,
    dryRun: false,
    force: false
  };
  while (tokens.length) {
    const token = tokens.shift();
    if (!allowed.has(token)) throw new UsageError(`unsupported option for ${command}: ${token}`);
    if (token === "--json") { options.json = true; continue; }
    if (token === "--dry-run") { options.dryRun = true; continue; }
    if (token === "--force") { options.force = true; continue; }
    const value = tokens.shift();
    if (value === undefined || value.startsWith("--")) {
      throw new UsageError(`option ${token} requires a value`);
    }
    if (token === "--target") {
      if (!TARGET_NAMES.includes(value)) throw new UsageError(`unsupported target: ${value}`);
      options.target = value;
    } else if (token === "--scope") {
      if (!SCOPES.has(value)) throw new UsageError(`unsupported scope: ${value}`);
      options.scope = value;
    } else if (token === "--document-profile") {
      if (!DOCUMENT_PROFILES.has(value)) throw new UsageError(`unsupported document profile: ${value}`);
      options.documentProfile = value;
    } else {
      options.projectDir = value;
    }
  }
  return { command, options, help: false };
}

function homeDirectory(env) {
  return env.USERPROFILE || env.HOME || os.homedir();
}

function resolveContext(command, options, cwd, env) {
  const manifestPath = path.join(PACKAGE_ROOT, "MANIFEST.json");
  const manifest = loadManifest(manifestPath);
  const errors = validateManifest(manifest, PACKAGE_ROOT);
  if (errors.length) {
    const failure = new Error(errors.join("; "));
    failure.command = command;
    throw failure;
  }
  const targetName = options.target === "auto" ? detectTarget({ env }) : options.target;
  const adapter = getAdapter(targetName, { homeDir: homeDirectory(env), env });
  const projectDir = options.scope === "project"
    ? path.resolve(options.projectDir || cwd)
    : null;
  const targetRoot = adapter.resolveSkillRoot(options.scope, projectDir);
  const documentStatus = documentProfileStatus(options.documentProfile, {
    packageRoot: PACKAGE_ROOT
  });
  const installerStatus = {
    state: "ready",
    evidence: [`manifest=${manifestPath}`, `package_root=${PACKAGE_ROOT}`, `node=${process.version}`],
    action: []
  };
  return {
    manifest,
    targetName,
    adapter,
    targetRoot,
    documentStatus,
    installerStatus,
    scope: options.scope,
    documentProfile: options.documentProfile
  };
}

function coreOptions(context, options) {
  return {
    packageRoot: PACKAGE_ROOT,
    targetRoot: context.targetRoot,
    manifest: context.manifest,
    targetName: context.targetName,
    scope: context.scope,
    runtimeProfile: context.documentProfile,
    documentProfile: context.documentProfile,
    documentStatus: context.documentStatus,
    discoveryVerifier: (skillName) => context.adapter.discoveryVerify(skillName),
    dryRun: options.dryRun
  };
}

function runDoctor(context, env) {
  const python = pythonRuntimeStatus({ env });
  return {
    code: 0,
    payload: {
      command: "doctor",
      target: context.targetName,
      scope: context.scope,
      target_root: context.targetRoot,
      runtime_detected: context.adapter.detect(),
      installer_status: context.installerStatus,
      document_profile: context.documentProfile,
      document_status: context.documentStatus,
      python_runtime: python,
      can_install: context.installerStatus.state === "ready" &&
        context.documentStatus.state === "ready",
      can_execute_documents: python.state === "ready",
      mutation_performed: false
    }
  };
}

function runInstall(context, options, env) {
  const python = pythonRuntimeStatus({ env });
  const plan = installSkill(coreOptions(context, options));
  return {
    code: 0,
    payload: {
      ...plan,
      command: "install",
      python_runtime: python,
      document_execution_blocked: python.state !== "ready"
    }
  };
}

function runVerify(context, env) {
  const target = context.targetRoot;
  const python = pythonRuntimeStatus({ env });
  const blocked = python.state !== "ready";
  if (!existsSync(target)) {
    return {
      code: 2,
      payload: {
        command: "verify",
        target,
        passed: false,
        installation_passed: false,
        violations: ["installation target missing"],
        python_runtime: python,
        document_execution_blocked: blocked
      }
    };
  }
  const verification = verifyInstallation(target);
  const violations = [...verification.violations];
  if (blocked) {
    violations.push("document runtime unavailable: Python 3.10-3.13 is required");
  }
  const passed = verification.passed && !blocked;
  return {
    code: passed ? 0 : 2,
    payload: {
      command: "verify",
      target,
      ...verification,
      violations,
      installation_passed: verification.passed,
      passed,
      python_runtime: python,
      document_execution_blocked: blocked
    }
  };
}

function runUninstall(context, options) {
  const result = uninstallSkill(context.targetRoot, { force: options.force });
  return {
    code: 0,
    payload: { command: "uninstall", target: context.targetRoot, ...result }
  };
}

function render(payload) {
  switch (payload.command) {
    case "doctor":
      return [
        "command: doctor",
        `target: ${payload.target}`,
        `scope: ${payload.scope}`,
        `target_root: ${payload.target_root}`,
        `runtime_detected: ${payload.runtime_detected}`,
        `installer_status: ${payload.installer_status.state}`,
        `document_profile: ${payload.document_profile}`,
        `document_status: ${payload.document_status.state}`,
        `python_runtime: ${payload.python_runtime.state}`,
        `can_install: ${payload.can_install}`,
        `can_execute_documents: ${payload.can_execute_documents}`,
        "mutation_performed: false"
      ].join("\n");
    case "verify":
      return [
        "command: verify",
        `target: ${payload.target}`,
        `passed: ${payload.passed}`,
        `installation_passed: ${payload.installation_passed}`,
        ...payload.violations.map((violation) => `violation: ${violation}`)
      ].join("\n");
    case "uninstall":
      return [
        "command: uninstall",
        `target: ${payload.target}`,
        `removed: ${payload.removed.length}`,
        `preserved_root: ${payload.preserved_root}`
      ].join("\n");
    default:
      if (payload.state === "dry-run") {
        return [
          "command: install",
          "state: dry-run",
          `target: ${payload.target}`,
          `payload_files: ${payload.payload_files.length}`,
          `stale_owned_files: ${payload.stale_owned_files.length}`,
          `document_profile: ${payload.document_profile}`
        ].join("\n");
      }
      return [
        "command: install",
        `state: ${payload.state}`,
        `target: ${payload.target}`
      ].join("\n");
  }
}

function emit(write, json, payload) {
  write(json ? JSON.stringify(payload) : render(payload));
}

export function run(argv, io = {}) {
  const json = argv.includes("--json");
  const write = io.stdout || ((text) => process.stdout.write(`${text}\n`));
  const writeError = io.stderr || ((text) => process.stderr.write(`${text}\n`));
  const cwd = io.cwd || process.cwd();
  const env = io.env || process.env;
  const fallbackCommand = argv.find((token) => COMMANDS.has(token)) ?? null;
  try {
    const parsed = parseArgs(argv);
    if (parsed.help) {
      write(HELP_TEXT);
      return 0;
    }
    const context = resolveContext(parsed.command, parsed.options, cwd, env);
    const result = parsed.command === "doctor" ? runDoctor(context, env)
      : parsed.command === "install" ? runInstall(context, parsed.options, env)
      : parsed.command === "verify" ? runVerify(context, env)
      : runUninstall(context, parsed.options);
    emit(write, json, result.payload);
    return result.code;
  } catch (error) {
    const payload = {
      state: "failed",
      error: error.message,
      command: error.command ?? fallbackCommand
    };
    if (json) emit(write, true, payload);
    else writeError(`error: ${error.message}`);
    return 2;
  }
}

function isEntryPoint() {
  const entry = process.argv[1];
  if (!entry) return false;
  const self = fileURLToPath(import.meta.url);
  try {
    return realpathSync.native(entry).toLowerCase() === realpathSync.native(self).toLowerCase();
  } catch {
    return path.resolve(entry).toLowerCase() === self.toLowerCase();
  }
}

export function main(argv = process.argv.slice(2)) {
  const code = run(argv);
  process.exitCode = code;
  return code;
}

if (isEntryPoint()) main();
