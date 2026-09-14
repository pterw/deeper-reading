import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmdirSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync
} from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { withTargetLock } from "./locking.js";
import {
  InstallerError,
  managedPath,
  payloadHashes,
  sha256File,
  validateManifest
} from "./manifest.js";

const RECEIPT_NAME = ".install-receipt.json";

function sortedObject(value) {
  if (Array.isArray(value)) return value.map(sortedObject);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, sortedObject(value[key])])
    );
  }
  return value;
}

// Single deep owner of receipt-parsed installation state. Every mutation or
// verification flow consumes this instead of re-parsing the receipt,
// re-validating the payload map, or re-walking owned paths. Containment is
// resolved here for every owned entry and is mandatory: strict consumers
// (upgrade, uninstall) fail closed through requireOwnedInstallation, while
// verify inspects problems.containment without bypassing containment.
function loadOwnedInstallation(targetRoot, options = {}) {
  const target = path.resolve(targetRoot);
  const loaded = {
    target,
    receiptPath: path.join(target, RECEIPT_NAME),
    receipt: null,
    owned: {},
    files: [],
    problems: {
      receiptMissing: false,
      receiptInvalid: null,
      ownershipMissing: false,
      containment: []
    }
  };
  if (!existsSync(loaded.receiptPath)) {
    loaded.problems.receiptMissing = true;
    return loaded;
  }
  try {
    loaded.receipt = JSON.parse(readFileSync(loaded.receiptPath, "utf8"));
  } catch (error) {
    loaded.problems.receiptInvalid = error.message;
    return loaded;
  }
  const owned = loaded.receipt.payload_hashes;
  if (!owned || typeof owned !== "object" || Array.isArray(owned) || Object.keys(owned).length === 0) {
    loaded.problems.ownershipMissing = true;
    return loaded;
  }
  loaded.owned = owned;
  const resolved = resolveOwnedMap(target, owned, { strict: false });
  loaded.files = resolved.files;
  loaded.problems.containment = resolved.containment;
  return loaded;
}

function requireOwnedInstallation(loaded, messages) {
  if (loaded.problems.receiptMissing) {
    throw new InstallerError(messages.missing);
  }
  if (loaded.problems.receiptInvalid !== null) {
    throw new InstallerError(`invalid installation receipt: ${loaded.problems.receiptInvalid}`);
  }
  if (loaded.problems.ownershipMissing) {
    throw new InstallerError(messages.ownership);
  }
  if (loaded.problems.containment.length) {
    throw new InstallerError(loaded.problems.containment.join("; "));
  }
  return loaded;
}

// Resolve an expected relative-path -> hash map into contained candidates.
// Containment is evaluated for every entry; strict consumers throw on the
// first escape, tolerant consumers collect the messages.
function resolveOwnedMap(targetRoot, expectedHashes, { strict = true } = {}) {
  const target = path.resolve(targetRoot);
  const files = [];
  const containment = [];
  for (const [relativePath, expected] of Object.entries(expectedHashes)) {
    let candidate;
    try {
      candidate = managedPath(target, relativePath);
    } catch (error) {
      if (strict) throw error;
      containment.push(error.message);
      continue;
    }
    files.push({ relativePath, expected, candidate });
  }
  return { files, containment };
}

// One hash walk over resolved owned files. The presence/matches pair lets
// each flow apply its own policy: upgrade treats a missing owned file as a
// modification, uninstall treats it as nothing to remove, and verify reports
// both as predicate failures.
function inspectOwnedFiles(files) {
  return files.map(({ relativePath, expected, candidate }) => {
    const present = existsSync(candidate) && statSync(candidate).isFile();
    return { relativePath, present, matches: present && sha256File(candidate) === expected };
  });
}

function verifyInstalled(targetRoot, expectedHashes) {
  const errors = [];
  if (!existsSync(path.join(targetRoot, "SKILL.md"))) {
    errors.push("missing canonical SKILL.md at installed root");
  }
  const { files } = resolveOwnedMap(targetRoot, expectedHashes);
  for (const file of inspectOwnedFiles(files)) {
    if (!file.present) errors.push(`missing payload file: ${file.relativePath}`);
    else if (!file.matches) errors.push(`payload hash mismatch: ${file.relativePath}`);
  }
  return errors;
}

function upgradeOwnership(targetRoot, expectedHashes) {
  const loaded = requireOwnedInstallation(loadOwnedInstallation(targetRoot), {
    missing: "existing target is unmanaged; installation receipt missing",
    ownership: "existing target has no managed payload ownership record"
  });
  const modified = inspectOwnedFiles(loaded.files)
    .filter((file) => !file.matches)
    .map((file) => file.relativePath)
    .sort();
  if (modified.length) {
    throw new InstallerError(`modified managed files: ${modified.join(", ")}`);
  }
  return new Set(Object.keys(loaded.owned).filter((relativePath) => !(relativePath in expectedHashes)));
}

function directoryTree(root) {
  if (!existsSync(root)) return [];
  const directories = [];
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory()) continue;
    const child = path.join(root, entry.name);
    directories.push(child, ...directoryTree(child));
  }
  return directories;
}

function pruneOwnedFiles(stage, staleOwned) {
  const deepestFirst = [...staleOwned].sort(
    (left, right) => right.split("/").length - left.split("/").length
  );
  for (const relativePath of deepestFirst) {
    const candidate = managedPath(stage, relativePath);
    if (existsSync(candidate) && statSync(candidate).isFile()) unlinkSync(candidate);
  }
  for (const directory of directoryTree(stage).sort((left, right) => right.length - left.length)) {
    try {
      rmdirSync(directory);
    } catch (error) {
      if (!["ENOTEMPTY", "EEXIST", "ENOENT"].includes(error.code)) throw error;
    }
  }
}

function copyPayload(packageRoot, stage, manifest) {
  for (const raw of manifest.payload) {
    const source = managedPath(packageRoot, raw);
    const destination = managedPath(stage, raw);
    mkdirSync(path.dirname(destination), { recursive: true });
    cpSync(source, destination, {
      recursive: statSync(source).isDirectory(),
      force: true,
      preserveTimestamps: true,
      filter: (candidate) => !["__pycache__", ".pytest_cache"].includes(path.basename(candidate))
    });
  }
}

function prepare(options) {
  const packageRoot = path.resolve(options.packageRoot);
  const targetRoot = path.resolve(options.targetRoot);
  const errors = validateManifest(options.manifest, packageRoot);
  if (errors.length) throw new InstallerError(errors.join("; "));
  if (options.documentStatus.state !== "ready") {
    throw new InstallerError(`Document profile not ready: ${options.documentStatus.state}`);
  }
  const expectedHashes = payloadHashes(packageRoot, options.manifest);
  const hadTarget = existsSync(targetRoot);
  const staleOwned = hadTarget
    ? upgradeOwnership(targetRoot, expectedHashes)
    : new Set();
  return { packageRoot, targetRoot, expectedHashes, hadTarget, staleOwned };
}

export function buildInstallPlan(options) {
  const prepared = prepare(options);
  return {
    state: "dry-run",
    target: prepared.targetRoot,
    payload_files: Object.keys(prepared.expectedHashes).sort(),
    stale_owned_files: [...prepared.staleOwned].sort(),
    document_profile: options.documentProfile
  };
}

export function installSkill(options) {
  if (options.dryRun) return buildInstallPlan(options);
  return withTargetLock(options.targetRoot, (targetRoot) => installLocked({ ...options, targetRoot }));
}

function installLocked(options) {
  const prepared = prepare(options);
  const { packageRoot, targetRoot, expectedHashes, hadTarget, staleOwned } = prepared;
  const parent = path.dirname(targetRoot);
  mkdirSync(parent, { recursive: true });
  const token = randomUUID();
  const name = path.basename(targetRoot);
  const stage = path.join(parent, `.${name}.stage-${token}`);
  const backup = path.join(parent, `.${name}.backup-${token}`);
  let replaced = false;
  const inject = (point) => options.failureInjector?.(point);
  try {
    if (hadTarget) {
      cpSync(targetRoot, stage, { recursive: true, preserveTimestamps: true });
      pruneOwnedFiles(stage, staleOwned);
    } else {
      mkdirSync(stage);
    }
    copyPayload(packageRoot, stage, options.manifest);
    const stagedErrors = verifyInstalled(stage, expectedHashes);
    if (stagedErrors.length) throw new InstallerError(stagedErrors.join("; "));
    inject("after-stage");

    if (hadTarget) {
      renameSync(targetRoot, backup);
      inject("after-backup");
    }
    renameSync(stage, targetRoot);
    replaced = true;
    inject("after-replace");

    const installedErrors = verifyInstalled(targetRoot, expectedHashes);
    if (installedErrors.length) throw new InstallerError(installedErrors.join("; "));
    inject("after-verify");

    let discoveryState = "not-available";
    let discoveryEvidence = [];
    if (options.discoveryVerifier) {
      const discovery = options.discoveryVerifier(options.manifest.skill.name);
      discoveryState = discovery.state;
      discoveryEvidence = discovery.evidence || [];
      if (!new Set(["verified", "not-available"]).has(discoveryState)) {
        throw new InstallerError(
          `host discovery verification failed: ${discoveryState}: ${discoveryEvidence.join(", ")}`
        );
      }
    }

    const receipt = {
      skill: options.manifest.skill.name,
      version: readFileSync(path.join(packageRoot, "VERSION"), "utf8").trim(),
      target: options.targetName,
      scope: options.scope,
      installed_root: targetRoot,
      runtime_profile: options.runtimeProfile,
      document_profile: options.documentProfile,
      document_status: options.documentStatus,
      host_discovery: { state: discoveryState, evidence: discoveryEvidence },
      payload_hashes: expectedHashes,
      installed_at: new Date().toISOString()
    };
    writeFileSync(
      path.join(targetRoot, RECEIPT_NAME),
      `${JSON.stringify(sortedObject(receipt), null, 2)}\n`,
      "utf8"
    );
    inject("after-receipt");
    rmSync(backup, { recursive: true, force: true });
    return { state: "installed", target: targetRoot, receipt };
  } catch (error) {
    try {
      rmSync(stage, { recursive: true, force: true });
      if (replaced) rmSync(targetRoot, { recursive: true, force: true });
      if (existsSync(backup)) renameSync(backup, targetRoot);
    } catch (rollbackError) {
      throw new InstallerError(`${error.message}; rollback failed: ${rollbackError.message}`);
    }
    if (error instanceof InstallerError) throw error;
    throw new InstallerError(error.message);
  } finally {
    rmSync(stage, { recursive: true, force: true });
    if (existsSync(backup) && existsSync(targetRoot)) {
      rmSync(backup, { recursive: true, force: true });
    }
  }
}

export function verifyInstallation(targetRoot) {
  const target = path.resolve(targetRoot);
  const predicates = {
    canonical_root: false,
    receipt_written: false,
    payload_hashes_match: false,
    document_profile_resolved: false,
    runtime_document_profile_consistent: false,
    receipt_matches_installed_root: false,
    host_discovery_verified_or_explicitly_not_available: false,
    no_staging_leftovers: false,
    no_backup_leftovers: false
  };
  const violations = [];
  predicates.canonical_root = existsSync(path.join(target, "SKILL.md")) &&
    !existsSync(path.join(target, path.basename(target), "SKILL.md"));
  if (!predicates.canonical_root) {
    violations.push("canonical SKILL.md missing or nested incorrectly");
  }
  const receiptPath = path.join(target, RECEIPT_NAME);
  if (!existsSync(receiptPath)) {
    violations.push("installation receipt missing");
    return { passed: false, predicates, violations };
  }
  predicates.receipt_written = true;
  const loaded = loadOwnedInstallation(target);
  if (loaded.problems.receiptInvalid !== null) {
    violations.push(`invalid receipt: ${loaded.problems.receiptInvalid}`);
    return { passed: false, predicates, violations };
  }
  const receipt = loaded.receipt;

  let hashOk = true;
  if (loaded.problems.ownershipMissing) {
    hashOk = false;
    violations.push("receipt has no managed payload ownership record");
  }
  for (const message of loaded.problems.containment) {
    hashOk = false;
    violations.push(message);
  }
  for (const file of inspectOwnedFiles(loaded.files)) {
    if (!file.present || !file.matches) {
      hashOk = false;
      violations.push(`payload hash mismatch or missing: ${file.relativePath}`);
    }
  }
  predicates.payload_hashes_match = hashOk && Object.keys(loaded.owned).length > 0;
  predicates.document_profile_resolved = receipt.document_status?.state === "ready" &&
    Boolean(receipt.document_profile);
  if (!predicates.document_profile_resolved) violations.push("document profile is not resolved");
  predicates.runtime_document_profile_consistent = !(
    receipt.document_profile === "oai-native" && receipt.runtime_profile !== "oai-native"
  );
  if (!predicates.runtime_document_profile_consistent) {
    violations.push(
      `inconsistent runtime/document profiles: ${JSON.stringify(receipt.runtime_profile)} with ${JSON.stringify(receipt.document_profile)}`
    );
  }
  predicates.receipt_matches_installed_root = receipt.installed_root === target;
  if (!predicates.receipt_matches_installed_root) {
    violations.push("receipt installed_root does not match verified target");
  }
  predicates.host_discovery_verified_or_explicitly_not_available =
    new Set(["verified", "not-available"]).has(receipt.host_discovery?.state);
  if (!predicates.host_discovery_verified_or_explicitly_not_available) {
    violations.push(`host discovery state is not acceptable: ${JSON.stringify(receipt.host_discovery?.state)}`);
  }
  const siblingNames = existsSync(path.dirname(target))
    ? readdirSync(path.dirname(target))
    : [];
  predicates.no_staging_leftovers = !siblingNames.some(
    (name) => name.startsWith(`.${path.basename(target)}.stage-`)
  );
  predicates.no_backup_leftovers = !siblingNames.some(
    (name) => name.startsWith(`.${path.basename(target)}.backup-`)
  );
  if (!predicates.no_staging_leftovers) violations.push("staging leftovers remain");
  if (!predicates.no_backup_leftovers) violations.push("backup leftovers remain");
  return { passed: Object.values(predicates).every(Boolean), predicates, violations };
}

export function uninstallSkill(targetRoot, options = {}) {
  return withTargetLock(targetRoot, (target) => uninstallLocked(target, options));
}

function uninstallLocked(targetRoot, options) {
  const target = path.resolve(targetRoot);
  const loaded = requireOwnedInstallation(loadOwnedInstallation(target), {
    missing: "installation receipt missing; refusing unmanaged operation",
    ownership: "installation receipt has no managed payload ownership record"
  });
  const modified = inspectOwnedFiles(loaded.files)
    .filter((file) => file.present && !file.matches)
    .map((file) => file.relativePath)
    .sort();
  if (modified.length && !options.force) {
    throw new InstallerError(`modified owned files: ${modified.join(", ")}`);
  }
  const removed = [];
  for (const item of [...loaded.files].sort(
    (left, right) => right.relativePath.split("/").length - left.relativePath.split("/").length
  )) {
    if (existsSync(item.candidate) && statSync(item.candidate).isFile()) {
      unlinkSync(item.candidate);
      removed.push(item.relativePath);
    }
  }
  const receiptPath = path.join(target, RECEIPT_NAME);
  if (existsSync(receiptPath)) unlinkSync(receiptPath);
  for (const directory of directoryTree(target).sort((left, right) => right.length - left.length)) {
    try {
      rmdirSync(directory);
    } catch (error) {
      if (!["ENOTEMPTY", "EEXIST", "ENOENT"].includes(error.code)) throw error;
    }
  }
  try {
    rmdirSync(target);
  } catch (error) {
    if (!["ENOTEMPTY", "EEXIST", "ENOENT"].includes(error.code)) throw error;
  }
  return { state: "uninstalled", removed, preserved_root: existsSync(target) };
}
