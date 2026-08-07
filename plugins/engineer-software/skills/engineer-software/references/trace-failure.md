# Trace Failure

Find an evidenced cause before editing production behavior.

## Enter

Use this module for a bug, exception, failing check, intermittent symptom, or performance regression
whose cause or failure mechanism is not yet established. If the cause and change boundary are already
known, use `deliver-change` instead.

## Execute

1. Build the cheapest decisive feedback signal at the smallest stable seam: a focused test, command,
   request replay, browser scenario, trace replay, benchmark, or bounded harness.
2. Reproduce the user's exact symptom. Distinguish a failing assertion from broken setup and record
   pre-existing unrelated failures separately.
3. Minimize the reproduction while preserving the failure. Raise the reproduction rate before
   debugging a flaky case; control time, randomness, concurrency, or inputs when possible.
4. Form only the competing hypotheses the evidence justifies. Rank them by observed facts and give
   each a falsifiable prediction. Do not require a ceremonial fixed count.
5. Test one prediction or causal variable at a time. Prefer a debugger or targeted boundary probe;
   tag temporary instrumentation so it can be found and removed.
6. For performance, establish a repeatable metric and baseline before changing code. Use profiling,
   query plans, or bisection rather than general logging.
7. Confirm the cause by showing that it predicts the symptom and that a controlled change or probe
   removes or alters the symptom as expected. Check a plausible alternative when confusion remains.
8. Remove temporary instrumentation and retain the minimized reproduction as regression evidence
   when it exercises the real failure path.

When debugging an agent or live process, do not ingest an actively written transcript or event log
wholesale. Use bounded tails, time filters, completed runs, external logs, or a stable copied snapshot
so the observation cannot recursively consume its own output.

If no reliable signal can be built, stop with the exact attempts and request the smallest missing
artifact or access: logs, trace, fixture, environment, or permission for bounded instrumentation.
Do not fill the gap with speculation.

## Exit

- Report the reproduced symptom, causal evidence, affected boundary, and ruled-out alternatives.
- If the user requested a fix and its scope is now closed, return to the router and enter
  `deliver-change`, carrying the reproduction as baseline evidence.
- If the cause exposes a broader unresolved design choice, enter `shape-work` before implementation.
