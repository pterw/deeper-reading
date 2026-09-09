# Task 2 RED — Hard-Standalone Release Contract

Baseline: v0.1.0 immutable archive SHA-256 `d1bfcfd54c8d70831ae73feb19446e7182cbb25fa28fb93e4861822174c310c4`.

Focused command:

`python -m pytest -q tests/test_hard_standalone_release_contract.py`

Result: **6 failed / 0 passed**.

Expected failures:

1. Runtime payload still names external Superpowers machinery in 10 files: `SKILL.md`, `README.md`, `references/anti-patterns.md`, `references/control-flow.md`, `references/definition-of-done.md`, `references/failure-recovery.md`, `references/pdf.md`, `references/prerequisites.md`, `references/runtime-profiles.md`, `scripts/verify_run.py`.
2. `MANIFEST.json` still contains required `superpowers` prerequisite.
3. Root `SKILL.md` compatibility still requires a Superpowers discovery mechanism.
4. `installer.core.install_skill` still requires a `superpowers` parameter.
5. `scripts/verify_run.py` still requires the old preflight keys `using_superpowers_read`, `superpowers_list_consumed`, `applicable_skills_read`, `live_dependencies_read`.
6. `scripts/verify_run.py` still uses old process-event vocabulary `systematic_debugging` and `brainstorming` instead of package-native document states.

This RED is the required precondition for Task 3. No production files were modified to satisfy it.
