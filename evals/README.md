# Routing evaluations

`routing-cases.json` is the runtime-neutral source of truth for skill activation and module routing.
Each case is self-contained and records the prompt, expected activation or bypass, allowed
evidence-driven transitions, expected result shape, and reproducible fixture. Codex and DeepSeek
Harness consume the same canonical cases; the Harness side is currently a static projection check,
not a live model evaluation.

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

Run a live, read-only routing sample through the installed Codex plugin:

```powershell
python scripts/run_routing_eval.py --live --public-submission --output evals/runs/local-routing-results.json
```

Live results are environment-dependent evidence, not deterministic CI fixtures. The runner uses an
ephemeral read-only Codex task and records only the route decision. `evals/runs/` is ignored so
model output is never committed accidentally. DeepSeek Harness live routing is not claimed until
the official preview exposes a stable, locally runnable evaluation surface. Review failed cases
manually before changing the skill; a model disagreement is a signal to inspect prompt ambiguity,
not an automatic expected-route rewrite.
