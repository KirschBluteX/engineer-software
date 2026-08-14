# Inspect Structure

Find architecture, design, policy, and implementation redundancy with code evidence.

## Enter

Use this module for a read-only structural audit or when a local change cannot establish the correct
owner or abstraction boundary. Do not treat aesthetic preference, file count, or unfamiliarity as a
finding. Implementation is out of scope until the user accepts a change boundary.

## Execute

1. Define the inspected subsystem, user-visible behavior, protected contracts, and evidence needed
   for a credible finding. Read relevant domain terms and decision records before judging intent.
2. Trace responsibilities from public entry points through callers, dependencies, data ownership,
   state transitions, and tests. Identify the current authoritative owner for each rule or concept.
3. Look for evidenced candidates:
   - duplicate responsibility, policy, validation, state, or data representation;
   - parallel implementations or adapters with no distinct contract;
   - pass-through wrappers or public interfaces that expose as much complexity as they hide;
   - knowledge scattered across callers, dependency cycles, or ownership leakage;
   - permanent old/new paths, dead adapters, or configuration that preserves two sources of truth;
   - tests forced onto private helpers because no stable behavioral seam exists.
4. For each candidate, cite paths, symbols, callers, and observable maintenance or correctness cost.
   Apply a deletion or merge thought experiment: say where the complexity would go and whether the
   result concentrates ownership or merely moves code.
5. Exclude or qualify intentional duplication before reporting it:
   - migration or compatibility paths with a documented end condition;
   - real platform or deployment differences;
   - generated code, vendor code, fixtures, snapshots, and protocol mirrors;
   - security, safety, or fault isolation;
   - measured performance-critical duplication;
   - an explicit architecture decision record whose trade-off still applies.
6. Rank only surviving findings by evidence, user impact, change leverage, and reversibility. For each,
   recommend keep, merge, delete, re-home, or investigate; include blast radius and verification needs.

Prefer a concise evidence table or prose report. Generate diagrams or a separate visual artifact only
when relationships are otherwise hard to understand or the user requests one.

## Exit

- If no candidate survives the false-positive checks, say so and identify the inspected boundary.
- Report findings without changing production structure.
- Before a system-level refactor, obtain user confirmation of the selected finding and boundary.
  Then enter `shape-work` if behavior or compatibility remains open; otherwise enter `deliver-change`.
