# Failure Recovery State Machine

A failure is a state transition, not permission to improvise.

## First failure

```text
node_failed
  -> STOP
  -> debugging-document-workflows
  -> read exact error/output
  -> isolate smallest failed boundary
  -> failure_diagnosed
```

Do not traverse to a sibling, fallback, later chunk, or downstream node before `failure_diagnosed`.

## After diagnosis

Choose the smallest response supported by evidence.

### Scope/timeout failure
Emit `node_rechunked` and split only the failed chunk. Verified upstream work is preserved.

### Tool-specific failure
Use the fallback documented by the governing format/reference contract, then emit `node_recovered` only after the failed boundary is proved healthy.

### Dependency/ingress failure
Prove the dependency or failed ingress plane first; change only the failed boundary.

### Fidelity/semantic conflict
Emit `architecture_stop`. Do not execute a semantics-changing workaround directly.

## Architecture-stop threshold

After **three** failed fix/repair attempts, or earlier when evidence shows the current path is not viable, enter `architecture_stop`. After this state, **do not attempt a fourth fix** or continued repair.

The only valid continuation is:

```text
architecture_stop
  -> paths_exhausted
  -> disclosure
  -> recovering-document-workflows
  -> alternative_designed
  -> plan_revised
  -> execution resumes
```

`disclosure` must identify the exact failed node, evidence/root cause, recovery branches already tried, upstream work still valid, remaining unverified work, and any authority/fidelity/task-semantic change.

## Completion path

If all failures are resolved within the traversal plan:

```text
all required nodes + canonical chunks complete
  -> verifying-exhaustive-traversal
  -> verification_started
  -> fresh proof from current source bytes
  -> verification_passed
  -> done
```

Any material event after `verification_passed` makes that proof stale.
