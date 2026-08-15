# Engineer Software 中文入口

[六个路由模块](#六个路由模块) · [工作原理](#工作原理) · [真实示例](#真实示例) · [Codex 安装](#codex安装升级卸载与调用) · [DeepSeek Harness](#deepseek-harness安装升级卸载与项目级技能) · [English README](README.md)

**一个面向 AI 编程代理、运行时中立、证据驱动的软件工程工作流。**

让代理在动手改代码前，先选择最小且可信的工程动作。

Engineer Software 是一个可安装到 Codex 和 DeepSeek Harness 的技能。面对模糊需求或原因
未知的故障时，它不会让代理直接跳到修改代码，而是只选择一个边界明确的工作流，并规定
代理在切换方向或宣布完成前必须提供哪些新证据。

概览：6 个边界明确的工作流 · 25 个确定性路由用例 · 2 个运行入口 · 1 份
canonical source（规范源）

## 六个路由模块

模块是可选的起点，不是每项任务都必须走完的流水线：

| 模块 | 何时使用 | 离开时应有的证据 |
| --- | --- | --- |
| **Shape Work** | 行为、范围、兼容性或验收条件仍不清楚 | 最小充分契约与明确排除项 |
| **Trace Failure** | 已有症状，但根因未知 | 可复现步骤与因果证据 |
| **Probe Choice** | 一个明确的设计决策需要一次性实验 | 观察结果及其决策后果 |
| **Deliver Change** | 目标和编辑边界已经确定 | 聚焦检查、实现结果和最终状态证据 |
| **Inspect Structure** | 问题是归属、重复或边界，而非单点修复 | owner/caller 追踪与边界建议 |
| **Manage Work Items** | 需要本地 PRD、任务拆分或验收清单 | 本地工件、依赖和验收条件 |

普通解释、翻译、简单读码和明确的机械文件操作会绕过路由，不增加流程负担。

> **示例：**“结账服务在高负载下偶尔生成重复订单。”技能会先进入 **Trace Failure**，要求
> 获得稳定复现和因果证据，然后才允许转入实现与最终验证。

## 30 秒理解

![Engineer Software 双运行时工作流封面，Codex 与 DeepSeek Harness 共享一份规范技能并进入证据验证](plugins/engineer-software/assets/engineer-software-cover.png)

Engineer Software 是一个精简路由器：它先判断请求是否存在实质性的工程不确定性，再选择一个最小而聚焦的模块，并要求用新证据证明何时可以离开该模块。

- Codex 与 DeepSeek Harness 是两个一等运行入口。
- 两个运行时共享同一份 canonical `SKILL.md`、`references/` 和路由评测。
- Harness 的 `.dsh/skills/` 内容是从 Codex canonical source 生成的投影，不是手工维护的第二套工作流。
- 普通解释、翻译、简单读码和明确的机械文件操作会绕过路由，不增加流程负担。

技术细节仍以英文 [README](README.md) 和 canonical [SKILL.md](plugins/engineer-software/skills/engineer-software/SKILL.md) 为准；本文件是中文用户入口，不复制维护完整技能正文。

## 工作原理

这套工作流是一个小型决策循环，不是每项任务都必须走完的仪式化流水线：

1. 先判断请求是普通工作，还是存在会影响结果的工程不确定性。
2. 只启动一个主要模块，并明确它需要什么证据才能离开。
3. 只有新证据关闭当前问题、并证明另一个问题确实出现时，才切换模块。
4. Codex 与 DeepSeek Harness 加载同一份 canonical `SKILL.md`、references 和路由用例。

![双运行时共享核心流程](docs/assets/runtime-neutral-flow.svg)

`.dsh/skills/` 是从 Codex canonical source 生成并检查的投影，不是第二套手工维护的工作流。
官方 Harness 来源、loader 契约和兼容边界见 [docs/compatibility.md](docs/compatibility.md)。

## 真实示例

每个示例都遵循同一条路径：用户请求 → 路由模块 → 继续推进前必须拿到的证据。

- “结账服务在高负载下偶尔生成重复订单。请找出原因并修复。” → **Trace Failure** →
  先稳定复现、证明根因，再加入聚焦回归测试。
- “在选择方案前，用一次性实验比较两个状态转换模型。” → **Probe Choice** →
  观察明确的取舍，并记录它对决策的影响。
- “为已有 status 命令增加已经定义的 `--json` 输出，并验证输出契约。” → **Deliver Change** →
  直接实现已关闭的契约，并验证最终状态。
- “解释这个函数做什么，以及为什么这里返回 null。” → **Bypass** →
  直接回答，不增加工程工作流负担。

这些示例对应 [`evals/routing-cases.json`](evals/routing-cases.json)，可以通过下方“验证”中的确定性命令运行；
它们帮助判断路由是否合适，不是速度排名。

## Codex：安装、升级、卸载与调用

### 安装

在 Codex 中添加 marketplace 并安装插件：

```powershell
codex plugin marketplace add KirschBluteX/engineer-software
codex plugin add engineer-software@engineer-software
codex plugin list
```

安装后开始一个新任务，让技能目录刷新；对实质性软件工程请求直接描述目标即可，也可以显式调用 `$engineer-software`。

### 升级

```powershell
codex plugin marketplace upgrade engineer-software
codex plugin add engineer-software@engineer-software
codex plugin list
```

升级后重新开始任务。若 canonical 技能内容发生变化，仓库维护者会同步生成 Harness 投影。

### 卸载

使用已安装的 Codex 插件管理器移除（示例）：

```powershell
codex plugin remove engineer-software@engineer-software
codex plugin list
```

具体参数以本机 Codex CLI 的帮助输出为准；本项目不包装或模拟 Codex 管理器。

### 调用示例

```text
$engineer-software
请为现有 status 命令增加已经定义的 --json 输出，并给出实现和验证证据。
```

如果请求只是解释一个函数或翻译文本，技能会按设计绕过，不会强行进入工程模块。

## DeepSeek Harness：安装、升级、卸载与项目级技能

Harness 运行时和 Engineer Software 技能是两层独立内容：先按官方方式运行 Harness，再把本项目生成的技能投影放入目标 workspace 的 `.dsh/skills/`。本项目不会替你安装或修改 Harness 本体。

### 1. 安装或首次运行 Harness

官方 README 当前推荐通过 npm 按需运行。安装 Node.js 后执行：

```powershell
npx @deepseek-ai/dsh web
```

这会下载并运行官方 npm 包，默认在 `http://127.0.0.1:3080` 启动 Web UI；它不会向 Engineer Software 仓库添加 Node 依赖，也不要求全局安装 `dsh`。请从官方 [DeepSeek Harness README](https://github.com/deepseek-ai/deepseek-harness#run) 核对最新入口。

### 2. 升级 Harness 运行时

官方文档目前没有定义单独的 `dsh upgrade` 命令。需要明确使用 npm 当前发布版本时，可以先查看版本，再用 npm 的 `latest` 标签启动：

```powershell
npm view @deepseek-ai/dsh version
npx @deepseek-ai/dsh@latest web
```

`@latest` 是 npm 的版本选择机制，不是本项目发明的 Harness 升级 API。Harness 仍处于 developer preview；升级后应重新执行本文的技能同步和静态兼容检查。

### 3. 在项目中安装 Engineer Software 技能

DeepSeek Harness 官方技能加载契约支持项目根目录下的 `.dsh/skills/<name>/SKILL.md` 及其相对资源。本仓库已经提交由 canonical source 生成的：

```text
.dsh/skills/engineer-software/SKILL.md
.dsh/skills/engineer-software/references/*.md
```

直接把本仓库作为 Harness workspace 时，只需检查默认投影：

```powershell
python scripts/sync_harness_skill.py --check
python scripts/validate_harness.py --check
npx @deepseek-ai/dsh web
```

要把技能安装到另一个项目，请在 Engineer Software 仓库根目录将目标显式传给生成器：

```powershell
$TargetProject = "C:\path\to\your-project"
python scripts/sync_harness_skill.py --write `
  --target "$TargetProject\.dsh\skills\engineer-software"
python scripts/validate_harness.py --check `
  --target "$TargetProject\.dsh\skills\engineer-software"
```

随后在 Harness 中选择 `$TargetProject` 对应的 workspace。提交生成文件前先审阅它们，并根据目标项目策略决定是否跟踪 `.dsh/skills/`。

### 4. 升级 Engineer Software 技能

先把 Engineer Software checkout 更新到你已审查的版本；对于正在跟踪远端分支的 checkout，可以使用 `git pull --ff-only`。随后对同一目标重复生成和检查：

```powershell
git pull --ff-only
$TargetProject = "C:\path\to\your-project"
python scripts/sync_harness_skill.py --write `
  --target "$TargetProject\.dsh\skills\engineer-software"
python scripts/validate_harness.py --check `
  --target "$TargetProject\.dsh\skills\engineer-software"
```

如果目标就是本仓库，可省略 `--target`。生成器不会删除陈旧文件；若检查报告额外文件，应先审阅，再明确删除。不要直接编辑 `.dsh/skills/` 投影，也不要手工维护第二套 `SKILL.md` 或 references。

### 5. 卸载

按本文推荐的 `npx` 方式运行 Harness 时，不会创建需要本项目卸载的全局 Harness 包；停止运行中的进程即可。Engineer Software 的项目级卸载只删除该技能自己的目录，不要删除其他 `.dsh` 配置或技能：

```powershell
Get-Item .dsh/skills/engineer-software
Remove-Item -LiteralPath .dsh/skills/engineer-software -Recurse
```

若安装在另一个项目，请在确认目标绝对路径后，对该项目中的 `.dsh/skills/engineer-software/` 执行同样操作。完整的用户级目录和故障排查见 [docs/compatibility.md](docs/compatibility.md)。

## 兼容边界与证据状态

本项目对照的是官方 [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness)，不是同名社区库，也不是 DeepSeek 官方插件、官方合作伙伴或官方贡献者。

| 项目 | 状态 |
| --- | --- |
| Codex marketplace/plugin 路径 | 保持原有路径，已在仓库校验中验证 |
| Harness `.dsh/skills` 项目级投影 | 已按官方文档做静态兼容验证；官方 loader smoke 已在 `0.1.0-rc.6` 做过 |
| canonical source 与 Harness 投影 | 字节一致性和相对 references 已检查 |
| Harness 版本稳定性 | **developer preview**，可能出现兼容性破坏变更 |
| Harness loader smoke | 官方 `0.1.0-rc.6` 已在项目 workspace 中发现并加载技能 |

完整矩阵、官方来源、升级故障处理和用户级目录说明见 [docs/compatibility.md](docs/compatibility.md)。官方 loader smoke 不需要 API key。

## 验证

要求 Python 3.9 或更高版本。开发校验依赖在 `requirements-dev.txt` 中：

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate_project.py
python -m unittest discover -s tests -v
python -m compileall -q scripts tests
```

`validate_project.py` 已聚合插件包、路由夹具、Harness 投影和文档契约。需要定位单项失败时，
再分别运行 `python scripts/validate_plugin.py plugins/engineer-software`、`python
scripts/validate_evals.py` 或 `python scripts/validate_harness.py --check`。

无需模型访问即可运行路由夹具：

```powershell
python scripts/run_routing_eval.py --limit 5
```

本 README 不发布单一速度提升百分比。任务级 A/B 结果用于观察路由、证据、范围和验证行为；
只有在相同条件下重复运行时，才使用配对汇总器及其可选时延门禁。原始格式、评分标准和解释
边界见 [行为 A/B 指南](evals/README.md#task-level-behavior-ab)。

上面的门禁聚焦 projection、路由夹具和 loader contract。另有一次官方 loader smoke：真实
`0.1.0-rc.6` 进程在本仓库 workspace 中发现并加载了 `engineer-software`，并解析其相对
references 资源。

## 常见问题

**为什么 Harness 找不到技能？**

确认启动 workspace 是本仓库，并检查路径是否精确为 `.dsh/skills/engineer-software/SKILL.md`；然后运行 `python scripts/validate_harness.py --check`。从无关目录启动可能会选择不同项目根。

**为什么投影检查报告 drift？**

只编辑 `plugins/engineer-software/skills/engineer-software/`，再运行 `python scripts/sync_harness_skill.py --write`。不要手工维护两份 `SKILL.md` 或 references。

**Harness 升级后加载失败怎么办？**

记录 Harness 版本或 commit，重新运行静态 probe，并参考官方技能文档；这是 developer preview 的兼容性风险，不要从同名社区库猜 manifest 或安装命令。

**能否把 API key 写入仓库配置？**

不能。静态检查不需要 key；模型凭据属于用户的运行时配置，不应出现在 README、fixtures、日志或提交中。

## 安全与隐私边界

本项目只提供指令和校验脚本，不包含 MCP server、hook、遥测、凭据存储或后台服务。宿主运行时仍可能访问用户授权的工具、代码和模型服务；请在提交前审阅生成文件，避免把 secrets、`.env`、session logs、个人数据或未经审阅的截图放入仓库。

更多政策： [SECURITY.md](SECURITY.md) · [PRIVACY.md](PRIVACY.md) · [TERMS.md](TERMS.md)。

## 继续阅读

- [英文 README](README.md)：项目首屏、完整示例和发布说明
- [运行时兼容矩阵](docs/compatibility.md)：官方 Harness 来源与边界
- [贡献指南](CONTRIBUTING.md)：canonical source、投影同步和检查门禁
- [路线图](ROADMAP.md)：精简的后续计划与非目标

欢迎先阅读 [英文 canonical skill](plugins/engineer-software/skills/engineer-software/SKILL.md)，再按上面的运行时入口开始工作。
