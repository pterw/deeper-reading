import { createHash } from "node:crypto";
import {
  accessSync,
  constants,
  existsSync,
  lstatSync,
  readlinkSync,
  readFileSync,
  readdirSync,
  realpathSync,
  statSync
} from "node:fs";
import path from "node:path";

export class InstallerError extends Error {}

const EXCLUDED_DIRECTORIES = new Set(["__pycache__", ".pytest_cache"]);
const WINDOWS_DRIVE = /^[A-Za-z]:/;

export function physicalPath(candidate, links = 0) {
  const absolute = path.resolve(candidate);
  if (links > 40) throw new InstallerError(`too many symbolic links: ${absolute}`);
  try {
    if (lstatSync(absolute).isSymbolicLink()) {
      // Resolve dangling aliases too: the target can temporarily be absent
      // between backup and replacement while its sibling lock remains held.
      return physicalPath(path.resolve(path.dirname(absolute), readlinkSync(absolute)), links + 1);
    }
    return realpathSync.native(absolute);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    const parent = path.dirname(absolute);
    if (parent === absolute) return absolute;
    return path.join(physicalPath(parent, links), path.basename(absolute));
  }
}

function isInside(root, candidate) {
  const relative = path.relative(root, candidate);
  return relative === "" || (
    relative !== ".." &&
    !relative.startsWith(`..${path.sep}`) &&
    !path.isAbsolute(relative)
  );
}

export function managedPath(root, raw) {
  if (typeof raw !== "string" || raw.trim() === "")
    throw new InstallerError("managed payload path must be a non-empty relative path");
  const normalized = raw.replaceAll("\\", "/");
  const parts = normalized.split("/");
  if (
    normalized.startsWith("/") ||
    normalized.startsWith("//") ||
    WINDOWS_DRIVE.test(normalized) ||
    parts.some((part) => part === "" || part === "." || part === "..")
  ) throw new InstallerError(`managed payload path escapes install root: ${JSON.stringify(raw)}`);
  const physicalRoot = physicalPath(root);
  const candidate = physicalPath(path.join(root, ...parts));
  if (!isInside(physicalRoot, candidate))
    throw new InstallerError(`managed payload path escapes install root: ${JSON.stringify(raw)}`);
  return candidate;
}

export function loadManifest(manifestPath) {
  return JSON.parse(readFileSync(manifestPath, "utf8"));
}

function frontmatterName(skillPath) {
  const text = readFileSync(skillPath, "utf8");
  const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n/);
  if (!match) return null;
  const name = match[1].split(/\r?\n/).find((line) => line.startsWith("name:"));
  return name ? name.slice(5).trim().replace(/^["']|["']$/g, "") : null;
}

export function validateManifest(manifest, packageRoot) {
  const errors = [];
  const root = physicalPath(packageRoot);
  if (manifest?.skill?.entrypoint !== "SKILL.md")
    errors.push("Canonical entrypoint must be SKILL.md");
  const skillPath = path.join(root, "SKILL.md");
  if (!existsSync(skillPath)) errors.push("Missing canonical SKILL.md at package root");
  else if (frontmatterName(skillPath) !== manifest?.skill?.name)
    errors.push("Manifest skill name does not match SKILL.md name");
  const payload = manifest?.payload;
  if (!Array.isArray(payload) || payload.length === 0)
    errors.push("Payload must be a non-empty list");
  const seen = new Set();
  for (const raw of Array.isArray(payload) ? payload : []) {
    if (typeof raw !== "string" || raw === "") {
      errors.push("Payload entries must be non-empty strings");
      continue;
    }
    if (seen.has(raw)) errors.push(`Duplicate payload entry: ${raw}`);
    seen.add(raw);
    try {
      const resolved = managedPath(root, raw);
      if (!existsSync(resolved)) errors.push(`Payload entry does not exist: ${raw}`);
    } catch (error) {
      errors.push(error.message);
    }
  }
  if (manifest?.prerequisites?.superpowers)
    errors.push("Standalone manifest must not require an external process framework");
  if (JSON.stringify(Object.keys(manifest?.document_profiles ?? {}).sort()) !== JSON.stringify(["oai-native", "standalone"]))
    errors.push("Document profiles must be exactly standalone and oai-native");
  if (!Array.isArray(payload) || !payload.includes("skills"))
    errors.push("Standalone runtime payload must include package-owned skills");
  return errors;
}

function walk(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    if (EXCLUDED_DIRECTORIES.has(entry.name)) continue;
    const candidate = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...walk(candidate));
    else if (entry.isFile()) files.push(candidate);
  }
  return files;
}

export function payloadFiles(packageRoot, manifest) {
  const root = physicalPath(packageRoot);
  const files = [];
  for (const raw of manifest.payload) {
    const candidate = managedPath(root, raw);
    if (statSync(candidate).isDirectory()) files.push(...walk(candidate));
    else files.push(candidate);
  }
  return [...new Set(files)].sort((a, b) => a.localeCompare(b));
}

export function sha256File(filePath) {
  accessSync(filePath, constants.R_OK);
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

export function payloadHashes(packageRoot, manifest) {
  const root = physicalPath(packageRoot);
  return Object.fromEntries(payloadFiles(root, manifest).map((file) => [
    path.relative(root, file).split(path.sep).join("/"),
    sha256File(file)
  ]));
}
