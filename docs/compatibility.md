# Runtime compatibility

Engineer Software is one runtime-neutral workflow. Codex and DeepSeek Harness are independent
entry points over the same canonical skill source; this document records the loading contracts and
the evidence we can verify locally.

## Official Harness facts

The implementation follows the official [`deepseek-ai/deepseek-harness`](https://github.com/deepseek-ai/deepseek-harness)
repository, not similarly named community libraries.

- The official README labels DeepSeek Harness (`dsh`) **developer preview** and warns of
  compatibility-breaking changes.
- The official [skills subsystem](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/subsystems/skills.md)
  scans project roots in this order: `.dsh/skills`, `.agents/skills`, configured custom roots, and
  user roots. A skill bundle is `<name>/SKILL.md` with relative resources such as `references/`.
- The official [plugin publishing guide](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/develop/basic/publish.md)
  defines a `package.json` `dsh.bundle.patch` format for executable Cordis composition layers. It
  does not define a stable remote manifest for a Markdown-only skill.

The repository therefore ships a checked-in `.dsh/skills/engineer-software/` projection generated
from `plugins/engineer-software/skills/engineer-software/`. It is a real project-local Harness
entry, not a claim of an official DeepSeek plugin or partnership. Run the deterministic probe:

The local contract review used official `master` commit
[`47f943859bef60e4160492346772ded9b24f765a`](https://github.com/deepseek-ai/deepseek-harness/commit/47f943859bef60e4160492346772ded9b24f765a)
on 2026-08-13. Recheck the upstream docs before treating this preview contract as stable.

```powershell
python scripts/validate_harness.py --check
```

The probe verifies file identity, frontmatter, resource paths, and the one-source rule. It is a
deterministic local check for the documented filesystem skill bundle.

### Local loader smoke (not a CI gate)

During this audit (2026-08-14 UTC), the official `@deepseek-ai/dsh@0.1.0-rc.6` package was started with an isolated
`DSH_HOME` and the repository selected as a workspace. Its real `FileSystemSkillProvider` returned
`engineer-software` from the `project-dsh` root at rank 100 and `get()` loaded the projected
`SKILL.md` body with its generated `references/` resource base. This records the filesystem loader
contract for a pinned preview package; rerun it after Harness preview upgrades before treating the
result as current.

## Compatibility matrix

| Surface | Codex | DeepSeek Harness | Evidence | Status |
| --- | --- | --- | --- | --- |
| Canonical workflow | `plugins/engineer-software/skills/engineer-software/` | same source projected to `.dsh/skills/engineer-software/` | byte-for-byte sync test | verified locally |
| Skill loader | Codex plugin manifest and marketplace | project `.dsh/skills/<name>/SKILL.md` | official docs + static probe + 0.1.0-rc.6 loader smoke | verified locally for that version; Harness preview |
| Relative references | `references/*.md` in plugin skill | copied generated `references/*.md` | projection check | verified locally |
| Routing fixtures | `evals/routing-cases.json` and Codex runner | shared cases checked against the generated skill tree | dual-tree case validation | static only |
| Install channel | Codex marketplace/plugin commands | project checkout or generated user skill root | commands below | Harness contract may change |

## Install, upgrade, and remove

### Codex

```powershell
codex plugin marketplace add KirschBluteX/engineer-software
codex plugin add engineer-software@engineer-software
codex plugin list
```

Start a new task after installation so the skill catalog is refreshed. To upgrade an existing
installation:

```powershell
codex plugin marketplace upgrade engineer-software
codex plugin add engineer-software@engineer-software
```

Remove it with `codex plugin remove engineer-software@engineer-software` and confirm with
`codex plugin list`. Command behavior is owned by the installed Codex CLI; this project does not
emulate or wrap that manager.

### DeepSeek Harness (project-local, recommended)

The project checkout already contains the generated entry. After pulling a change, regenerate and
check it from the repository root:

```powershell
python scripts/sync_harness_skill.py --write
python scripts/validate_harness.py --check
npx @deepseek-ai/dsh web
```

Choose this repository as the Harness workspace, then ask for a software change. The local provider
will discover `.dsh/skills/engineer-software/SKILL.md`; the six references remain relative to that
directory. The `npx` command and Web UI are documented by the official Harness README. Model
configuration is supplied by the user's Harness runtime.

To remove the project entry, delete the generated `.dsh/skills/engineer-software/` directory from
your checkout, or keep it and disable the skill in your Harness configuration. Do not edit the
projection by hand: rerun the sync command after changing the canonical source.

### DeepSeek Harness (user-global)

The official provider also scans `<dshHome>/skills`. A reviewed copy can be written to that root:

```powershell
python scripts/sync_harness_skill.py --write `
  --target "$env:USERPROFILE\.dsh\skills\engineer-software"
python scripts/validate_harness.py --check `
  --target "$env:USERPROFILE\.dsh\skills\engineer-software"
```

Use the equivalent `$DSH_HOME/skills/engineer-software` path on other systems. Removing that target
uninstalls the user-global copy; rerun `--write` after upgrading this repository. The command never
deletes stale files, so inspect and remove obsolete generated files deliberately.

## Troubleshooting

**The skill does not appear.** Confirm that Harness is using the intended workspace, that the path is
exactly `.dsh/skills/engineer-software/SKILL.md`, and run `python scripts/validate_harness.py --check`.
The project root is the nearest ancestor containing `.git`; launching from an unrelated directory
will select a different root.

**The skill appears but a reference cannot be loaded.** Run
`python scripts/sync_harness_skill.py --write`, then check for drift. Every reference must be under
the generated bundle's `references/` directory; nested recursive skill discovery is not part of the
official local provider contract.

**The projection check reports drift.** Edit only the canonical Codex tree, then regenerate. A
drift report is an integrity failure, not a reason to maintain a second hand-edited copy.

**A Harness upgrade breaks loading.** Treat this as a preview compatibility issue. Capture the
Harness commit/version, rerun the static probe, and consult the official repository's current skill
and plugin docs before changing this project. Do not infer a manifest or install command from a
community project with a similar name.

## Security boundary

The skill contains instructions only. It has no MCP server, hook, telemetry, credential handling, or
background process. Harness itself may execute tools and may ask for a DeepSeek API key; those
permissions belong to the user's Harness profile and workspace policy. Review generated files before
placing them in a user-global skill directory, and never commit API keys, `.env` files, session logs,
or Harness profile state.

## 中文入口

安装、升级、卸载、调用、兼容边界和常见问题见完整的
[简体中文 README](../README.zh-CN.md)。英文 README 与 canonical skill 仍是技术规范来源。
