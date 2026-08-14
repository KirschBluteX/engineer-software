# Public plugin submission

This file is the copy-ready source for the OpenAI plugin submission portal. Revalidate it against
the current portal before each submission.

## Submission type

- Type: Skills only
- Authentication: None
- MCP server: None
- External data collection by this package: None

## Info

| Field | Value |
| --- | --- |
| Plugin name | Engineer Software |
| Short description | Evidence-led software work |
| Developer | KirschBluteX |
| Category | Developer Tools |
| Website | https://github.com/KirschBluteX/engineer-software |
| Support | https://github.com/KirschBluteX/engineer-software/issues |
| Privacy | https://github.com/KirschBluteX/engineer-software/blob/main/PRIVACY.md |
| Terms | https://github.com/KirschBluteX/engineer-software/blob/main/TERMS.md |
| Logo | `plugins/engineer-software/assets/engineer-software-logo.svg` |

Long description:

> Routes software tasks to one bounded workflow for shaping, diagnosis, probes, implementation,
> structural review, or local planning.

## Starter prompts

1. Use Engineer Software to shape this change and define acceptance evidence.
2. Use Engineer Software to trace this failure before editing.
3. Use Engineer Software to deliver and verify this code change.

## Positive tests

Copy the full prompt, expected behavior, expected result, and fixture from these case IDs in
`evals/routing-cases.json`:

1. `direct-unclear-cache-behavior`
2. `direct-intermittent-duplicate`
3. `direct-state-model-experiment`
4. `direct-closed-feature`
5. `direct-duplicate-policy-audit`

Together they cover shaping, diagnosis, disposable decision probes, implementation, and structural
inspection. The full repository suite additionally covers local work items and every transition.

## Negative tests

1. `negative-explain-code`
2. `negative-mechanical-rename`
3. `negative-format-only`

Each should bypass the plugin because the work is ordinary explanation or a specified reversible
operation with no material software uncertainty.

## Initial release notes

Initial public submission of a skills-only software-engineering workflow. The package routes work to
one of six bounded modules, requires fresh acceptance evidence, preserves existing repository work,
keeps issue-tracker output local, and includes no MCP server, hook, telemetry, authentication, or
background service. The repository includes public-directory metadata and assets, 25 structured
routing cases, local validation, CI, privacy/support/security documents, and an optional live
read-only routing runner.

The same canonical workflow is also exposed through a generated project-local DeepSeek Harness
skill projection. DeepSeek Harness is a developer preview; this project makes no official
partnership, contributor, or live-API claim.

## Copy-ready launch text

Short:

> Runtime-neutral, evidence-driven software engineering workflow for AI coding agents.

Long:

> Engineer Software routes substantive software work through one bounded evidence-driven module at
> a time: shape unclear contracts, trace unknown failures, probe one decision, deliver defined
> changes, inspect structural redundancy, or draft local work items. Codex and DeepSeek Harness use
> one canonical source with deterministic projection checks.

Suggested GitHub repository description:

> A runtime-neutral, evidence-driven software engineering workflow for AI coding agents.

Suggested topics (choose only those that accurately describe the repository):

`ai-coding-agent`, `agent-skills`, `software-engineering`, `evidence-driven`, `codex`,
`deepseek-harness`, `dsh-plugin`

Suggested homepage: `https://github.com/KirschBluteX/engineer-software`

These are copy suggestions only. Do not represent `dsh-plugin` as an official registry, and do not
publish GitHub metadata from this repository without a separate publisher decision.

## Publisher-only final gate

Before selecting **Submit for Review**, the publisher must confirm:

- the selected OpenAI organization has Apps Management write access;
- the displayed individual or business identity is verified and exactly matches the publisher;
- the final uploaded skill tree matches the tested Git commit and plugin version;
- public availability regions are legally and operationally supported;
- website, support, privacy, and terms URLs are live;
- every portal test case is copied without altering its expected behavior;
- all policy attestations are accurate for the final package.

Submission begins OpenAI review; approval is followed by a separate publisher-controlled public
release in the universal Plugins Directory.
