# Deliver Change

Make the smallest sufficient production change and prove the final state.

## Enter

Use this module when the intended outcome, protected behavior, edit scope, and acceptance evidence are
closed enough to implement. Carry forward an established reproduction or decision contract instead of
restarting discovery. Return to `trace-failure` when the cause is still unknown.

## Execute

1. Inspect repository rules, the working tree, nearby tests, public contracts, and affected callers.
2. Establish before-change evidence at the cheapest decisive seam:
   - changed behavior: a focused check rejects the desired behavior for the expected reason;
   - defect: the real symptom reproduces;
   - behavior-preserving refactor: characterization or affected checks pass first;
   - performance: a repeatable baseline and target exist;
   - configuration or generated output: a parser, schema, build, snapshot, or smoke check exists.
3. Apply the conditional **structure-risk gate** only when the change adds or moves a module,
   interface, policy, validation rule, state owner, data representation, adapter, migration lane,
   broad responsibility, or copied nontrivial logic. Find the existing owner, comparable capability,
   and real callers; extend that owner instead of creating a parallel implementation. Keep policy,
   validation, state, and data representation single-sourced; preserve dependency direction; and
   reject wrappers, dual paths, or migration lanes without a net simplification and explicit removal
   condition. Skip the full gate for a narrow local edit with obvious ownership. If ownership or the
   safe boundary cannot be judged locally, stop and enter `inspect-structure`.
4. Change one independently verifiable behavior slice at a time. For new or changed behavior, write
   or strengthen the decisive check before production code when a correct seam exists, observe the
   expected failure, implement only enough to pass, and inspect the actual result.
5. Refactor only to remove evidenced duplication, leakage, or accidental complexity needed by the
   current change. Do not add speculative flags, factories, interfaces, extension points, or future
   behavior.
6. Re-run direct evidence after every later edit that can affect it. Then run affected checks and
   only the broader build, type, lint, schema, compatibility, or end-to-end checks justified by risk.
7. Inspect the final diff for scope drift, user-work damage, debug probes, disabled checks, stale
   dual paths, accidental generated output, and new responsibilities with no clear owner.

When no correct automated seam exists, use the strongest honest behavioral or manual evidence and
report the missing seam; do not add a shallow test that cannot observe the real contract.

## Exit

- If the structure-risk gate cannot establish an owner or safe boundary, stop before the structural
  edit, report the uncertainty, and enter `inspect-structure`.
- If evidence invalidates the assumed cause, stop stacking patches and enter `trace-failure`.
- If evidence invalidates the product or compatibility contract, enter `shape-work`.
- Otherwise report the changed behavior and scope, decisive starting evidence, fresh final
  verification with exact outcomes, structural-gate result when it ran, and any pre-existing failure
  or remaining uncertainty.
