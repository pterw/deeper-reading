# Control Flow

This reference defines the package-owned document state machine.

## 1. Establish the traversal contract

Read root `SKILL.md`, resolve the runtime profile, read the required references/format guide, and invoke the package-owned `exhaustive-document-traversal` module.

For substantial work, create a **document-specific** `<run-root>/plan.md` through `planning-document-traversal` before execution. Plans must enumerate source acquisition, extraction, canonical chunk generation, exhaustive chunk traversal, deliverables, failure boundaries, and final verification.

## 2. Execute bounded nodes

Use `executing-document-traversal` and decompose as:

```text
Task
  Batch
    Chunk
      Operation
```

A node advances only after its output is inspected and its proof recorded. One shell/container call contains one simple operational command.

## 3. Exhaustive traversal gate

The bundled extractor manifest defines the canonical chunk universe. Traverse chunks in ordinal order. For every chunk:

1. inspect exact content and locator;
2. write exactly one machine verdict in `evidence/chunk-evidence.json`;
3. use atomic extractive assertions/constraints for `evidence`, or explicit reason for `non_match`;
4. emit exactly one ordered `chunk_verified` event;
5. only then advance.

Finding the requested fact does not terminate traversal.

**Twelve emitted chunks require twelve** discrete evidence verdicts and twelve ordered `chunk_verified` events before Done is reachable. A **forged smaller manifest** cannot shrink that obligation: final verification re-extracts the original source with the bundled extractor and requires the reproduced canonical chunk universe to match exactly.

## 4. Failure diagnosis gate

At the first failed node:

```text
node_failed
  -> STOP
  -> debugging-document-workflows
  -> failure_diagnosed
```

No repair, re-chunk, sibling, fallback, later chunk, or downstream node is valid before `failure_diagnosed`.

After diagnosis, exactly one evidence-backed transition may occur:

- `node_rechunked` when bounded size/scope is the root cause;
- `node_recovered` after a semantics-preserving repair;
- documented sibling/fallback traversal;
- `architecture_stop` when the current path is no longer viable.

Preserve already-verified upstream work.

## 5. Architecture-stop / exhausted recovery gate

Once `architecture_stop` occurs, no fourth/continued repair is allowed. The only redesign path is:

```text
architecture_stop
  -> paths_exhausted
  -> disclosure
  -> recovering-document-workflows
  -> alternative_designed
  -> plan_revised
  -> execution resumes from smallest unresolved node
```

`disclosure` records the failed node, root cause, attempted recovery branches, upstream work still valid, unverified remainder, and any source/fidelity/task-semantic consequences.

## 6. Success gate

When every canonical chunk and required plan node is resolved:

```text
verifying-exhaustive-traversal
  -> verification_started
  -> re-extract original source
  -> reproduce canonical chunk universe
  -> prove exact evidence coverage + ordered chunk_verified events
  -> regenerate deterministic TRAVERSAL_REPORT.md
  -> verify source fidelity / format QA / plan / failures / deliverables
  -> verification_passed
  -> done
```

`done` is valid only when `verification_passed` occurs after the last material event. Any later material event makes verification stale and requires a fresh verification cycle.

## 7. Source/task invariants

Never silently transform:

```text
read source -> write review
extract source -> author summary
primary source -> secondary commentary
original file -> recreated substitute
verify source -> verify derivative
```

If a workaround changes source authority, fidelity, format semantics, or requested task semantics, use the architecture-stop/disclosure/replan gate before execution.
