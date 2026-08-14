# Probe Choice

Use throwaway code to answer one decision, then remove the experiment.

## Enter

Use this module only when a named logic, state, data-model, feasibility, performance, or interaction
question can be resolved more cheaply by running a bounded experiment than by discussion. A probe is
not a draft production implementation.

## Execute

1. State the question, competing outcomes, observation method, stop condition, and decision each
   possible result would support.
2. Place the probe where its context is clear but mark it unmistakably disposable. Avoid changing
   production paths unless the experiment specifically requires a controlled integration seam.
3. Build the minimum runnable slice. Prefer one inline or in-memory command when it can preserve the
   observation; otherwise mark a temporary file clearly. Avoid abstractions, options, or polish.
4. Make relevant state and results visible. Keep inputs fixed when comparing alternatives and use
   one command or scenario to repeat the observation.
5. Run the probe and record the result, uncertainty, and decision consequence. Stop when the named
   choice is answered; do not test adjacent dimensions unless they can reverse the decision.
6. Delete the probe after it answers the question, or retain it only with explicit user agreement
   and a clear expiry. Capture the decision in the requested durable artifact when one exists.

Do not promote a disposable implementation by renaming it. Reimplement the accepted behavior under
production constraints and tests.

## Exit

- If the result closes implementation, return to the router and enter `deliver-change`.
- If the result changes or leaves open the intended behavior, enter `shape-work`.
- If the experiment uncovers an unexplained failure, enter `trace-failure`.
- Otherwise report the answered question, observation, decision, and cleanup state.
