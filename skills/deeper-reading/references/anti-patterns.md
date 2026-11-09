# Anti-Patterns and Rationalizations

## Process anti-patterns

### Narrating instead of executing
Saying "I am using the skill" does not invoke or read it.

### Skipping package-owned process modules
Reading the root skill but bypassing the required planning, execution, debugging, recovery, or verification module defeats the runtime contract. Resolve the module required by the current state before continuing.

### Hard-coded external process vocabulary
External framework names are development context, not runtime protocol. The package-owned event schema is authoritative.

### Planning without executing
Writing a plan and then freelancing outside the package-owned execution protocol defeats the plan.

### Executing without planning
Substantial multi-step work needs the planning gate before tool churn begins.

### Moving after failure
Trying a sibling node or workaround before `failure_diagnosed` skips root-cause isolation.

### Brainstorming too early
`alternative_designed` is allowed only after `architecture_stop`, `paths_exhausted`, and `disclosure`, not after the first error.

### Broad retries
Retry the failed child, not the entire workflow.

## Document anti-patterns

### Summary substitution
"Read the paper" is not "write a review."

### QAing a derivative
A clean render of your summary proves the summary renders; it does not prove the source was read correctly.

### Extract-before-render
For PDF reading, extraction is helper evidence after source-page inspection.

### arXiv tunnel vision
The canonical publication may be publisher, proceedings, lab, author, or institutional HTML/PDF.

### HTML demotion
A complete official HTML publication is not an inferior source merely because a PDF exists.

### OCR by reflex
OCR is conditional and can be lossy.

### Structural blindness
Visual rendering cannot prove every DOCX/PDF structure; follow the live skill's structural checks.

## Tool anti-patterns

### Giant shell blob
Multiple operations in one call destroy failure boundaries and encourage timeouts.

### Skipping `--help`
Remembered CLI syntax is not current tool documentation.

### Dependency thrashing
Do not rebuild Python because optional JS is missing, or install Node because a Python path failed, without proving necessity.

### Network-plane conflation
Shell DNS failure does not prove browser/connector/direct-download failure.

### Stale verification
A previous successful render/test does not prove current state.

## Rationalization table

| Rationalization | Reality |
|---|---|
| "I already know the process." | Read the package-owned module required by the current state. |
| "The protocol hasn't changed." | The current package event schema, not memory, is authoritative. |
| "I can plan mentally." | Multi-step work gets a written plan. |
| "I'll try the fallback first." | Debug the failed node first. |
| "One more retry is quicker." | Repeating the same unit gives little new evidence. |
| "I can summarize while ingress is broken." | That silently changes the task. |
| "The extraction looks readable." | Source render/structure may contradict it. |
| "The file exists, so conversion worked." | Visual/structural verification is still required. |
| "The diff is nonzero, so layout changed." | Inspect the actual renders and diff. |
| "I verified this earlier." | Completion requires fresh evidence. |
