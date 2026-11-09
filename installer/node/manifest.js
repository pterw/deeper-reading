import { createHash } from "node:crypto";
import {
  accessSync,
  constants,
  existsSync,
  lstatSync,
  readFileSync,
  readdirSync,
  realpathSync,
  statSync
} from "node:fs";
import path from "node:path";

export class InstallerError extends Error {
  constructor(message, code) {
    super(message);
    if (code !== undefined) this.code = code;
  }
}

const EXCLUDED_DIRECTORIES = new Set(["__pycache__", ".pytest_cache"]);
const WINDOWS_DRIVE = /^[A-Za-z]:/;

// POSIX answers ENOTDIR for a name beneath a file; Windows answers ENOENT. Both mean the name is not there.
const ABSENT = ["ENOENT", "ENOTDIR"];

function isLink(candidate) {
  try {
    return lstatSync(candidate).isSymbolicLink();
  } catch (error) {
    if (ABSENT.includes(error.code)) return false;
    throw error;
  }
}

// Where a path really leads, for a path that need not exist yet: the filesystem's answer for the deepest part
// that exists, then the names beneath it, which cannot be links. A link that leads nowhere is refused, not guessed at.
export function physicalPath(candidate) {
  const absolute = path.resolve(candidate);
  const missing = [];
  for (let prefix = absolute; ; prefix = path.dirname(prefix)) {
    try {
      return path.join(realpathSync.native(prefix), ...missing);
    } catch (error) {
      if (error.code === "ELOOP") throw new InstallerError(`too many symbolic links: ${absolute}`);
      if (!ABSENT.includes(error.code)) throw error;
    }
    if (isLink(prefix)) {
      throw new InstallerError(
        `${absolute} passes through a link that leads nowhere: ${prefix}; create the folder it points to, or remove the link`
      );
    }
    if (path.dirname(prefix) === prefix) return absolute;
    missing.unshift(path.basename(prefix));
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

// The folder holding SKILL.md and the payload: `skill.root` (a POSIX path
// relative to the package root, default ".") resolved to a physical path.
export function skillRoot(manifest, packageRoot) {
  const root = physicalPath(packageRoot);
  const raw = manifest?.skill?.root;
  if (raw === undefined) return root;
  if (typeof raw !== "string") throw new InstallerError("skill.root must be a string");
  if (raw === "" || raw.includes("\\") || raw.startsWith("/") || WINDOWS_DRIVE.test(raw))
    throw new InstallerError("skill.root must be a relative path");
  const parts = raw.split("/");
  if (parts.includes("..")) throw new InstallerError("skill.root must not contain ..");
  const resolved = physicalPath(path.join(root, ...parts));
  if (!isInside(root, resolved)) throw new InstallerError("skill.root is outside the package root");
  return resolved;
}

export function validateManifest(manifest, packageRoot) {
  const errors = [];
  let root = null;
  try {
    root = skillRoot(manifest, packageRoot);
  } catch (error) {
    if (!(error instanceof InstallerError)) throw error;
    errors.push(error.message);
  }
  if (manifest?.skill?.entrypoint !== "SKILL.md")
    errors.push("Canonical entrypoint must be SKILL.md");
  let skillFound = false;
  if (root !== null) {
    const skillPath = path.join(root, "SKILL.md");
    if (!existsSync(skillPath)) errors.push("Missing canonical SKILL.md at package root");
    else {
      skillFound = true;
      if (frontmatterName(skillPath) !== manifest?.skill?.name)
        errors.push("Manifest skill name does not match SKILL.md name");
    }
  }
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
    if (root === null) continue;
    try {
      const resolved = managedPath(root, raw);
      if (skillFound && !existsSync(resolved)) errors.push(`Payload entry does not exist: ${raw}`);
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

function filesUnder(root, manifest) {
  const files = [];
  for (const raw of manifest.payload) {
    const candidate = managedPath(root, raw);
    if (statSync(candidate).isDirectory()) files.push(...walk(candidate));
    else files.push(candidate);
  }
  return [...new Set(files)].sort((a, b) => a.localeCompare(b));
}

export function payloadFiles(packageRoot, manifest) {
  return filesUnder(skillRoot(manifest, packageRoot), manifest);
}

export function sha256File(filePath) {
  accessSync(filePath, constants.R_OK);
  return createHash("sha256").update(readFileSync(filePath)).digest("hex");
}

export function payloadHashes(packageRoot, manifest) {
  const root = skillRoot(manifest, packageRoot);
  return Object.fromEntries(filesUnder(root, manifest).map((file) => [
    path.relative(root, file).split(path.sep).join("/"),
    sha256File(file)
  ]));
}
