---
name: shipping-a-change
description: How a deeper-reading release ships, from a dated CHANGELOG section to npm and the GitHub Release. Use before cutting a release.
---

# Shipping a change

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
