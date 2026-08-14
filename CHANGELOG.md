# Changelog

All notable changes to Engineer Software are documented here.

## [Unreleased]

- Reframed the project as a runtime-neutral workflow with Codex and DeepSeek Harness entry points.
- Added a checked, generated `.dsh/skills` projection, static Harness compatibility probe, shared
  routing fixtures checked against both skill trees, compatibility/install guidance, and a
  deterministic dual-runtime diagram.
- Added a non-branded engineering cover asset and copy-ready launch guidance without official
  endorsement or adoption claims.
- Disabled the CI `setup-python` pip cache because the repository has no cache dependency contract;
  the existing Python matrix and validation gates remain unchanged.
- Consolidated duplicate positive tests and CI commands behind the repository validator, removed a
  non-evidentiary Harness version probe, and tightened shared workflow rules without changing the
  six public routes.
- Recorded a keyless live-loader smoke against official Harness `0.1.0-rc.6`; model/API routing
  remains explicitly unverified.

## [0.1.0] - 2026-08-13

- Initial skills-only plugin release with six focused software-engineering workflows.
- Hardened public plugin metadata with square brand assets and policy links.
- Added structured direct, indirect, follow-up, boundary, and negative routing cases.
- Added reproducible plugin, routing, repository, CI, and release-preflight validation.
