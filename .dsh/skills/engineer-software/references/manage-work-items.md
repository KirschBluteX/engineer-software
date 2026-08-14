# Manage Work Items

Turn known context into reviewable local planning and triage artifacts.

## Enter

Use this module when the requested deliverable is a local PRD, vertical task breakdown, acceptance
brief, or triage draft. It does not discover an unknown failure or publish work to a remote tracker.

## Execute

1. Use the current conversation, repository evidence, domain vocabulary, accepted decisions, and
   supplied issue text. Inspect missing facts only when they can change the draft.
2. Choose the smallest requested artifact:
   - PRD: problem, outcome, users, behavior, constraints, acceptance, decisions, and exclusions;
   - tasks: thin end-to-end slices, acceptance checks, dependencies, and human decision points;
   - triage: type, current evidence, reproduction status when relevant, missing information, proposed
     state, and a durable implementation brief when ready.
3. Keep requirements observable and tasks independently verifiable. Prefer vertical slices that
   deliver a narrow complete behavior over layer-by-layer work packages.
4. Mark assumptions, unresolved product or architecture choices, and external prerequisites. Do not
   label a task autonomous when it still depends on an unstated human decision.
5. Return the local draft in the conversation or write it only to a user-selected repository path.
   Preserve parent material and avoid duplicating an existing authoritative plan.

Do not publish, comment, label, close, or mutate any remote tracker. If the user asks for remote
publication, prepare the reviewable draft and state that publication requires a separate explicitly
authorized workflow outside this skill.

## Exit

Report the artifact location or inline draft, source evidence, dependencies, unresolved decisions,
and the acceptance rule that makes each item ready. Stop after the requested artifact. If the user
also requested implementation and the first executable slice is closed, return to the router and
enter `deliver-change` for that slice only.
