# Routing evaluations

`routing-cases.json` is the runtime-neutral source of truth for expected skill activation and module routing.
Each case is self-contained and records the prompt, expected activation or bypass, allowed
evidence-driven transitions, expected result shape, and reproducible fixture. Codex and DeepSeek
Harness consume the same canonical cases through the checked canonical and generated skill trees.

The suite covers:

- direct, indirect, follow-up, boundary, and negative prompts;
- every primary module plus the bypass boundary;
- every transition documented by a module's `Exit` section;
- more than the public-directory minimum of five positive and three negative cases.

Validate the case contract without model access:

```powershell
python scripts/validate_evals.py
python scripts/validate_harness.py --check
```

The aggregate validator checks the case contract once against the canonical references, then the
Harness projection gate independently proves byte identity. This avoids a runtime-labelled duplicate
assertion over the same files. An audit-only loader smoke also confirmed that the official
`0.1.0-rc.6` filesystem provider discovers and loads the project skill.

Run a live, read-only routing sample through the installed Codex plugin:

```powershell
python scripts/run_routing_eval.py --live --public-submission --output evals/runs/local-routing-results.json
```

Live results are environment-dependent evidence, not deterministic CI fixtures. The runner uses an
ephemeral read-only Codex task and records only the route decision. `evals/runs/` is ignored so
model output is never committed accidentally. Review failed cases manually before changing the
skill; a model disagreement is a signal to inspect prompt ambiguity, not an automatic expected-route
rewrite.

## Task-level behavior A/B

`behavior-cases.json` contains a small, source-attributed pilot set: controlled reductions of public
SWE-Lancer Diamond issue/proposal tasks plus negative and planning controls. The reductions keep the
user language and decision pressure while using tiny local fixtures so the test does not require a
14 GB application image or an external service. They are stress cases, not a claim of benchmark
equivalence.

Prepare matched worktrees outside the repository, then run each condition with the same model and
permissions:

```powershell
python scripts/prepare_behavior_worktrees.py --output-root C:\path\to\worktrees
python scripts/run_behavior_eval.py --condition baseline --workspace-root C:\path\to\worktrees --live --output evals/runs/behavior-baseline.json
python scripts/run_behavior_eval.py --condition treatment --workspace-root C:\path\to\worktrees --live --output evals/runs/behavior-treatment.json
```

The default per-case timeout is 900 seconds because realistic engineering tasks can exceed a short
smoke-test window. Use the same timeout for both conditions and record any override.

Both conditions disable optional plugins and skill search so user configuration cannot add a second
treatment difference. The treatment prompt explicitly loads the repository's canonical `SKILL.md`;
the baseline prompt does not. Both runs record raw JSONL events, the final response, wall-clock
timestamps, the tracked patch, and hashed bounded content for untracked files. `completion_state`
separates a completed response, timeout, missing final response, and command failure; an
authentication or CLI failure is environment evidence, not a workflow score.
The runner ignores user configuration by default. If the selected model depends on a custom
provider in the active Codex config, add `--use-user-config` to both conditions and record that
configuration as part of the experiment; optional plugins remain disabled in both conditions.

Review each pair against the same rubric before comparing condition labels. Mask labels and paths
when practical, while recognizing that tool traces can reveal whether a skill was loaded. Higher
scores are better; use 1 and 3 for results between the anchored levels:

| Metric | 0 | 2 | 4 |
| --- | --- | --- | --- |
| `outcome` | wrong, missing, or harmful result | partially meets the request | fully meets the observable request |
| `evidence` | unsupported claims | useful evidence with material gaps | causal, traceable evidence for key claims |
| `scope` | harmful or unrelated changes | avoidable scope expansion | only requested changes; protected behavior preserved |
| `verification` | absent or falsely reported checks | narrow checks with important gaps | relevant before/after and final-state checks |
| `friction` | blocked or creates major rework | notable avoidable overhead | minimal time and steps without sacrificing correctness |

Combine the two raw `results` arrays, add one complete `scores` object per result with integer or
decimal values from 0 to 4 for all five metrics, then run:

```powershell
python scripts/summarize_behavior_eval.py evals/runs/behavior-scored.json
```

The summary rejects malformed or partial score objects instead of silently treating missing values
as zeros. It reports paired deltas, wins/ties/losses, and an exact two-sided sign-test p-value. Treat
these as descriptive evidence for this model, fixture set, and prompt sample; they do not establish a
general causal effect. A missing credential, timeout, or setup failure is environment evidence and
must remain separate from a workflow failure.
