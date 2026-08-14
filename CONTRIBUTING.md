# Contributing

Contributions should preserve the runtime-neutral thin router and one-primary-module contract.
Codex is the marketplace entry; DeepSeek Harness consumes the generated project skill projection.
Do not hand-edit or duplicate the workflow under `.dsh/skills/`.

## Development setup

Use Python 3.9 or newer:

```powershell
python -m pip install -r requirements-dev.txt
```

Before editing, inspect the worktree and the affected route's `Enter`, `Execute`, and `Exit`
contracts. Add or strengthen the focused case before changing routing behavior.

The editable source is only `plugins/engineer-software/skills/engineer-software/`. After changing
`SKILL.md` or a reference, regenerate and check the Harness projection:

```powershell
python scripts/sync_harness_skill.py --write
python scripts/validate_harness.py --check
```

The official Harness integration is project-local `.dsh/skills/<name>/SKILL.md` plus relative
resources. Harness is a developer preview; do not invent a remote manifest, claim live API coverage,
or describe the project as an official DeepSeek plugin.

## Required checks

```powershell
python scripts/validate_plugin.py plugins/engineer-software
python scripts/validate_evals.py
python scripts/validate_project.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
python scripts/validate_harness.py --check
```

For routing changes, add a self-contained case with expected activation, route, result shape, and
fixture. Keep every documented transition represented in `evals/routing-cases.json`. Live model
evidence belongs under ignored `evals/runs/`, never in a release commit.

The CI workflow intentionally leaves `actions/setup-python` pip caching disabled. This repository
has no `requirements.txt` or `pyproject.toml` cache contract; `requirements-dev.txt` is installed
explicitly for validation.

## Release policy

1. Keep the manifest version valid SemVer and use at most one `+codex.<cachebuster>` suffix.
2. Update `CHANGELOG.md` and the public-submission release notes.
3. Run all required checks and inspect the staged archive for secrets or generated files.
4. Tag the reviewed commit as `v<base-version>`; the release workflow validates, packages, and
   creates the GitHub release.
5. Submit the same final skill tree to the OpenAI plugin portal. Policy attestations and final
   publication remain explicit publisher actions.
