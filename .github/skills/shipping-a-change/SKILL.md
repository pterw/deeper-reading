---
name: shipping-a-change
description: How a deeper-reading release ships, from a dated CHANGELOG section to npm and the GitHub Release. Use before cutting a release.
---

# Shipping a change

## Cut a release

Before the first tag, the owner creates the `npm-release` environment with a
required reviewer and a `v*` tag rule.

The package exists on npm and its trusted publisher (`pterw/deeper-reading`,
`release.yml`, `npm-release`) is stage-only. npm rejects a plain `npm publish`
from CI, so the workflow stages the version and a person approves it.

For each release:

1. On the release branch, date the section: `## X.Y.Z - YYYY-MM-DD`.
   `python tools/release_check.py --tag vX.Y.Z` passes.
2. Optional rehearsal: run the Release workflow by hand on the branch (gates,
   label check, `npm publish --dry-run`, ZIP build; nothing ships). The manual
   run applies the same tag check.
3. The owner merges.
4. Tag the merge commit: `git tag -a vX.Y.Z -m "vX.Y.Z" <merge-sha>`. The owner
   pushes the tag. The tag must point at a commit on `main`; a tag that is not
   is refused before any approval is asked.
5. `.github/workflows/release.yml` re-runs the gates and waits. The owner
   approves the `npm-release` environment in Actions.
6. The `publish` job stages the version with `npm stage publish`.
7. The owner approves the staged version on the package's page on npmjs.com
   (Staged Packages tab) or with `npm stage approve <stage-id>`, with 2FA.
   Approval waits for npm's malware scan.
8. The `release` job starts right after the stage and waits up to 60 minutes
   for the version to be public on npm, so approve within that hour. It then
   makes the GitHub Release with the CHANGELOG section, the ZIP and its SHA-256.

A publish cannot be undone; npm refuses to reuse a version. A failure is fixed
by re-running the workflow, never by a new tag for the same version.

- A version already public on npm is skipped by `publish`, so a full re-run is
  safe.
- A version already staged makes the stage step fail: approve or reject it on
  npmjs.com first, then re-run.
- If the `release` job timed out waiting, approve the staged version, then
  re-run only that job. It publishes the existing release and replaces its
  assets. If the staged version was rejected or failed npm's scan, re-run the
  whole workflow instead: the version is missing, so it is staged again.
