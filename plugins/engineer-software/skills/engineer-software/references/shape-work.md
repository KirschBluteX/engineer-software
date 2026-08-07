# Shape Work

Close only the decisions that can invalidate implementation or its acceptance.

## Enter

Use this module when the intended behavior, scope, compatibility boundary, success condition,
or decision path is materially unresolved. Do not enter merely because a task is large.

## Execute

1. Inspect the current repository behavior, instructions, domain vocabulary, decision records,
   public contracts, and nearby conventions that can answer the open questions.
2. Frame the work in observable terms: user or system outcome, affected surface, constraints,
   non-goals, acceptance evidence, and irreversible or externally visible choices.
3. Separate confirmed facts, evidence-backed inferences, safe reversible defaults, and decisions
   that genuinely require the user.
4. Stress-test uncertain behavior with concrete examples, boundary cases, failure cases, and
   compatibility scenarios. Prefer a small example over abstract debate.
5. Ask at most one to three independent blocking questions together. Ask dependent questions
   only after their prerequisite is resolved. Include a recommendation when evidence supports one.
6. Record a durable architecture decision only when the choice is hard to reverse, surprising
   without context, and the result of a real trade-off. Otherwise keep the decision with the work.
7. Produce the smallest sufficient contract: outcome, scope, protected behavior, constraints,
   acceptance checks, and remaining explicit exclusions.

Do not force an interview, a repository map, multiple candidate plans, or a document artifact.
Stop shaping as soon as the next action is safe and testable.

## Exit

- If the user requested only a decision or plan, return the contract and its unresolved risks.
- If implementation is ready, return to the router and enter `deliver-change`.
- If a named uncertainty is best answered by a disposable experiment, enter `probe-choice`.
- If a symptom still lacks a cause, enter `trace-failure`.
- If the desired output is a PRD or task set, enter `manage-work-items`.

Exit evidence is a closed outcome and acceptance boundary, not agreement that every detail is known.
