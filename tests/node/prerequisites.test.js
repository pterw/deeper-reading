import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import {
  BUNDLED_EXTRACTORS,
  documentProfileStatus,
  pythonRuntimeStatus
} from "../../installer/node/prerequisites.js";

test("standalone package readiness depends on bundled extractors, not Python", (t) => {
  const root = mkdtempSync(path.join(os.tmpdir(), "deeper-reading-prereq-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  mkdirSync(path.join(root, "scripts"));
  for (const name of BUNDLED_EXTRACTORS)
    writeFileSync(path.join(root, "scripts", name), "# extractor\n", "utf8");
  assert.equal(documentProfileStatus("standalone", { packageRoot: root }).state, "ready");
  rmSync(path.join(root, "scripts", BUNDLED_EXTRACTORS[0]));
  assert.equal(documentProfileStatus("standalone", { packageRoot: root }).state, "missing");
});

test("Python status accepts 3.10 through 3.13 and blocks absence", () => {
  for (const version of ["3.10.14", "3.11.9", "3.12.8", "3.13.7"]) {
    const ready = pythonRuntimeStatus({
      candidates: [["python", []]],
      spawn: () => ({ status: 0, stdout: `${version}\n`, stderr: "" })
    });
    assert.equal(ready.state, "ready", version);
  }
  for (const version of ["3.9.19", "3.14.0", "2.7.18"]) {
    const unsupported = pythonRuntimeStatus({
      candidates: [["python", []]],
      spawn: () => ({ status: 0, stdout: `${version}\n`, stderr: "" })
    });
    assert.equal(unsupported.state, "blocked", version);
  }
  const blocked = pythonRuntimeStatus({
    candidates: [["python", []]],
    spawn: () => ({ status: 1, stdout: "", stderr: "not found" })
  });
  assert.equal(blocked.state, "blocked");
});
