# Chunking Document Workflows Restructure Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the custom document-workflow skill into a small control kernel plus focused references for prerequisites, HTML, PDF, DOCX, source acquisition, failure recovery, and anti-patterns.

**Architecture:** `SKILL.md` owns orchestration only. `references/` owns format- and failure-specific guidance. Superpowers is a prerequisite layer: `using-superpowers` -> `@Superpowers:superpowers` current skill listing -> select/read applicable skills -> `writing-plans` -> `executing-plans`; on a failed node invoke `systematic-debugging` before traversing elsewhere; after documented branches are exhausted invoke `brainstorming`; on success invoke `verification-before-completion`.

**Tech Stack:** Agent Skills Markdown, Superpowers plugin skills, OAI PDF/DOCX local skills.

**Spec:** User-approved architecture in this conversation.

## Global Constraints
- One shell command per tool call.
- Read current skills, task docs, and CLI help; do not rely on cached summaries.
- PDF/DOCX workflows delegate to current OAI skills rather than copying their full instructions.
- HTML is a first-class source type.
- No silent source/task/fidelity substitution.

### Task 1: Refactor control kernel
- [ ] Replace monolithic `SKILL.md` with orchestration, prerequisite discovery, planning/execution state machine, source classification, failure transitions, and verification gate.
- [ ] Link one level deep to all reference files.

### Task 2: Add dependency and format references
- [ ] Create `references/prerequisites.md`.
- [ ] Create `references/control-flow.md`.
- [ ] Create `references/dependencies.md`.
- [ ] Create `references/html.md`.
- [ ] Create `references/pdf.md`.
- [ ] Create `references/docx.md`.
- [ ] Create `references/source-acquisition.md`.
- [ ] Create `references/failure-recovery.md`.
- [ ] Create `references/anti-patterns.md`.

### Task 3: Verify
- [ ] Re-run the RED contract as GREEN.
- [ ] Parse YAML frontmatter and validate name/description constraints.
- [ ] Verify every linked reference exists and is one level deep.
- [ ] Verify required control-flow phrases and OAI skill paths exist.
- [ ] Read final `SKILL.md` and references back completely.
- [ ] Invoke `superpowers:verification-before-completion` before claiming completion.
