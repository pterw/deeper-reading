---
name: shipping-a-change
description: What to update when you change something in deeper-reading, how a release ships, and what done requires. Use before opening a pull request or cutting a release.
---

# Shipping a change

## Add a document format

1. Write `scripts/extract_<format>.py` on the `Block`, `pack_blocks` and
   `build_manifest` schema in `scripts/chunk_common.py`. It supports both
   `--out <path>` and `--run-root <path>`.
2. Register it in `EXTRACTOR_SCRIPTS` in `scripts/verify_run.py`.
3. Document the format's structural invariants in `references/<format>.md`.
4. Add the format's routes to `skills/exhaustive-document-traversal/SKILL.md`.
5. Add deterministic coverage in `tests/test_extractors.py` and
   `tests/test_phase_gated_loading.py`.
6. Verify: `python -m pytest -q tests/test_extractors.py tests/test_phase_gated_loading.py`

## When you change this, also change that

| When you change | Also update |
|---|---|
| `scripts/extract_*.py` | `tests/test_extractors.py`; re-extraction in `scripts/verify_run.py` accepts only what the extractor reproduces |
| A new document format | `scripts/extract_<format>.py`, `EXTRACTOR_SCRIPTS` in `scripts/verify_run.py`, `references/<format>.md`, the format routes in `skills/exhaustive-document-traversal/SKILL.md`, `tests/test_extractors.py`, `tests/test_phase_gated_loading.py` |
| `installer/*.py` or `installer/adapters/*.py` | the matching `installer/node/*.js`; `tests/node/parity.test.js` must still pass |
| What ships | `MANIFEST.json` `payload`, `package.json` `files`, `RELEASE_FILES` / `RELEASE_DIRECTORIES` in `installer/distribution.py` |
| Definition of Done predicates | `references/definition-of-done.md` and `PREDICATES` in `scripts/verification_findings.py` |
| The version | `VERSION`, `package.json`, `CHANGELOG.md`; grep `README.md` and `references/runtime-profiles.md` for the old version |
| Skill or reference prose | grep `tests/` for the file name and the phrase first |

## Cut a release

Before the first tag, the owner creates the `npm-release` environment with a
required reviewer and a `v*` tag rule.

The first release is bootstrapped by hand, because npm needs the package to
exist before a trusted publisher attaches. After the release pull request is
merged:

1. The owner runs `npm publish` from the merged commit on `main`, for the same
   version that is about to be tagged, logged in to an npm account with 2FA
   that can create the unscoped name `deeper-reading`.
2. The owner adds the trusted publisher: repository `pterw/deeper-reading`,
   workflow `release.yml`, environment `npm-release`.
3. The owner pushes the tag. The workflow finds that version on npm, skips the
   publish, and still makes the GitHub Release.

Then, for each release:

1. On the release branch, date the section: `## X.Y.Z - YYYY-MM-DD`.
   `python tools/release_check.py --tag vX.Y.Z` passes.
2. Optional rehearsal: run the Release workflow by hand on the branch (gates,
   label check, `npm publish --dry-run`, ZIP build; nothing ships). The manual
   run applies the same tag check.
3. After the owner merges, tag the merge commit:
   `git tag -a vX.Y.Z -m "vX.Y.Z" <merge-sha>`. The owner pushes the tag. The
   tag must point at a commit on `main`; a tag that is not is refused before
   any approval is asked.
4. `.github/workflows/release.yml` re-runs the gates, waits for the owner's
   approval of the `npm-release` environment, publishes to npm by trusted
   publishing (skipped if that version is already on npm), then makes the
   GitHub Release with the CHANGELOG section, the ZIP and its SHA-256.

A publish cannot be undone; npm refuses to reuse a version. A failure is fixed
by re-running the workflow, never by a new tag for the same version. A full
re-run is safe: `publish` skips a version already on npm. Re-running only the
`release` job after a partial failure publishes the existing release and
replaces its assets.

## Done

- `python -m pytest -q -rs` exits 0, and every skip reason is one that
  `tests/check_skip_budget.py` budgets.
- `npm test` exits 0 when `installer/`, `package.json` or `tests/node/` changed.
- `python tools/release_check.py` exits 0.
- A behaviour change ships with a test that fails without the change.
- A change to a published contract (CLI flags, `dod.json` fields, finding codes,
  chunk-manifest or evidence schema, install receipt) keeps old inputs working,
  or its CHANGELOG line names the break.
