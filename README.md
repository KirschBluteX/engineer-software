# Engineer Software

**A runtime-neutral, evidence-driven software engineering workflow for AI coding agents.**

[![CI](https://github.com/KirschBluteX/engineer-software/actions/workflows/ci.yml/badge.svg)](https://github.com/KirschBluteX/engineer-software/actions/workflows/ci.yml)

Choose the smallest trustworthy engineering move before changing code.

[Six workflows](#six-workflows) · [How it works](#how-it-works) · [Real examples](#real-examples) · [Quick start](#quick-start) · [Validation](#validation) · [简体中文](README.zh-CN.md)

Engineer Software gives Codex and DeepSeek Harness two runtime entries into one canonical workflow.
For substantive software work, it selects exactly one bounded engineering mode and defines the
evidence required before an agent can change direction or claim completion.

**At a glance:** 6 bounded workflows · 25 deterministic routing cases · 2 runtime paths · 1
canonical source

![Engineer Software runtime-neutral workflow cover showing Codex and DeepSeek Harness feeding one canonical skill into evidence verification](plugins/engineer-software/assets/engineer-software-cover.png)

**Use it when** requirements, failure mechanisms, design choices, implementation scope, structural
ownership, or acceptance evidence materially affect the result. **Bypass it when** the request is an
ordinary explanation, translation, simple code reading, formatting change, or already-specified
mechanical operation.

## Six workflows

The modules are alternative starting points, not a pipeline that every task must complete:

| Workflow | Start here when | Evidence required to leave |
| --- | --- | --- |
| **Shape Work** | behavior, compatibility, scope, or acceptance is unclear | smallest sufficient contract and explicit exclusions |
| **Trace Failure** | a symptom exists but its cause is unknown | reproduction plus causal evidence |
| **Probe Choice** | one named design decision needs a disposable experiment | observed result and decision consequence |
| **Deliver Change** | the outcome and edit boundary are closed | focused check, implementation result, and final-state evidence |
| **Inspect Structure** | ownership, duplication, or boundaries are the question | traced owners and callers plus a boundary recommendation |
| **Manage Work Items** | the requested output is a local PRD, task set, or acceptance list | local artifact with dependencies and acceptance criteria |

> **Example:** “Checkout sometimes creates a duplicate order under load.” The skill starts with
> **Trace Failure**, requires a reproduction and causal evidence, and only then allows a transition
> to implementation and final verification.

## How it works

The workflow is a small decision loop, not a ceremony-heavy pipeline:

1. The router checks whether the request is ordinary work or has material engineering uncertainty.
2. It starts one primary module and makes that module's exit evidence explicit.
3. A later module is entered only when fresh evidence closes the current module and identifies a
   different need.
4. Codex and DeepSeek Harness load the same canonical `SKILL.md`, references, and routing cases.

![Dual-runtime shared-core flow](docs/assets/runtime-neutral-flow.svg)

The Harness tree is generated and checked from the Codex source; it is not a second hand-maintained
workflow. See [runtime compatibility](docs/compatibility.md) for the official Harness sources,
loader contract, and compatibility limits.

## Real examples

Each example follows the same shape: prompt → route → evidence required to proceed.

- “Checkout sometimes creates a duplicate order under load. Find the cause and fix it.” →
  **Trace Failure** → reproduce the symptom, establish the cause, then add a focused regression.
- “Build a disposable experiment to compare two state-transition models before we choose one.” →
  **Probe Choice** → observe the named trade-off and record the decision consequence.
- “Add the documented `--json` flag to the existing status command and verify the specified output
  contract.” → **Deliver Change** → implement the closed contract and verify the final state.
- “Explain what this function does and why it returns null here.” → **Bypass** → answer directly
  without adding workflow overhead.

These examples are represented in [`evals/routing-cases.json`](evals/routing-cases.json).
Run the deterministic routing checks without model access:

```powershell
python scripts/validate_evals.py
python scripts/validate_harness.py --check
python scripts/run_routing_eval.py --limit 5
```

Optional live Codex evidence is read-only and environment-dependent:

```powershell
python scripts/run_routing_eval.py --live --public-submission `
  --output evals/runs/local-routing-results.json
```

The repository checks routing, projection identity, and evidence contracts. Task-level A/B runs are
sampled behavioral evidence, not a general benchmark claim. This README does not publish a single
speedup percentage; use the paired evaluator and optional latency gate only for like-for-like reruns.
See the [behavior A/B guide](evals/README.md#task-level-behavior-ab) for the raw format and scoring
limits.

## Quick start

### Codex

```powershell
codex plugin marketplace add KirschBluteX/engineer-software
codex plugin add engineer-software@engineer-software
codex plugin list
```

Start a new task after installation, then ask for a substantive software change or invoke
`$engineer-software`. Upgrade with:

```powershell
codex plugin marketplace upgrade engineer-software
codex plugin add engineer-software@engineer-software
```

Remove it with the installed Codex plugin manager and confirm the result:

```powershell
codex plugin remove engineer-software@engineer-software
codex plugin list
```

The existing Codex marketplace manifest and plugin path remain unchanged.

### DeepSeek Harness

DeepSeek Harness is an official open-source project, currently marked **developer preview**. Its
official local skill provider scans project `.dsh/skills` roots. This checkout includes a generated
projection of the canonical skill. Check it, start Harness, then choose this repository as the
workspace:

```powershell
python scripts/sync_harness_skill.py --check
python scripts/validate_harness.py --check
npx @deepseek-ai/dsh web
```

After updating a reviewed checkout or editing the canonical skill, regenerate and verify the same
project entry:

```powershell
git pull --ff-only
python scripts/sync_harness_skill.py --write
python scripts/validate_harness.py --check
```

Remove only this generated project entry after confirming the target:

```powershell
Get-Item .dsh/skills/engineer-software
Remove-Item -LiteralPath .dsh/skills/engineer-software -Recurse
```

A user-global copy can target `$DSH_HOME/skills/engineer-software`. Exact target commands,
troubleshooting, official contract sources, and the recorded loader smoke are in
[runtime compatibility](docs/compatibility.md).

## Validation

Use Python 3.9 or newer. The repository is standard-library-first; the development-only
`requirements-dev.txt` contains the YAML parser used by the validators.

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

`validate_project.py` aggregates the plugin package, routing fixtures, Harness projection, and
documentation contracts. For a focused failure, run `python scripts/validate_plugin.py
plugins/engineer-software`, `python scripts/validate_evals.py`, or `python
scripts/validate_harness.py --check` directly. CI keeps the Python 3.9/3.12/3.13 matrix plus the
aggregate validation, unittest, and compile checks. It leaves `setup-python`'s pip cache disabled;
the development file is installed explicitly.

## Compatibility, limits, and security

Read [docs/compatibility.md](docs/compatibility.md) for the matrix, install/upgrade/remove paths,
official DeepSeek Harness links, troubleshooting, and the static-contract and loader-smoke evidence.
The short version:

- DeepSeek Harness is a rapidly changing developer preview; compatibility-breaking changes are
  possible.
- The `.dsh/skills` tree is a generated projection. Edit the Codex canonical source and regenerate;
  drift fails validation.
- Engineer Software is not an official DeepSeek plugin, partnership, or endorsement, and it does not
  invent a Harness manifest outside the documented filesystem skill contract.
- This project does not ship an MCP server, hook, telemetry, credential store, or background
  service. Tool permissions, API keys, and model configuration remain the user's runtime policy.
- Never commit API keys, `.env` files, session logs, profile state, generated temporary assets, or
  unreviewed screenshots.

GitHub is a distribution target, not a runtime route. This repository performs no issue-tracker,
telemetry, or remote workflow action when a skill is used. See [PRIVACY.md](PRIVACY.md),
[SECURITY.md](SECURITY.md), and [TERMS.md](TERMS.md).

## Contributing and roadmap

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Keep `plugins/engineer-software/skills/engineer-software/`
as the only editable workflow source, run the projection check after changes, and add routing
fixtures for new transitions. [ROADMAP.md](ROADMAP.md) records the deliberately small next steps;
it does not promise a long-lived adapter framework.

## License

Engineer Software is released under the [MIT License](LICENSE).
