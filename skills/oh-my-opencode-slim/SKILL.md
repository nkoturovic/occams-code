---
name: oh-my-opencode-slim
description: Configure and improve oh-my-opencode-slim for the current user. Use when users want to tune agents, models, prompts, custom agents, skills, MCPs, presets, or plugin behavior. Also use when recurring workflow friction suggests a safe config or prompt improvement.
---

# oh-my-opencode-slim v2.1.1 Configuration Skill

Help users configure, customize, and safely improve their
oh-my-opencode-slim setup. Prefer the smallest durable change: tune models,
adjust prompts, add focused custom agents, restrict skills/MCPs, and document
restart requirements.

## When to Use

Use this skill when the user asks about or would clearly benefit from changes to:

- `~/.config/opencode/oh-my-opencode-slim.json[c]`
- `<project>/.opencode/oh-my-opencode-slim.json[c]`
- agent models, variants, presets, or provider routing
- project-local or user-level prompt overrides
- custom agents under `agents.<name>`
- custom agent `prompt` and `orchestratorPrompt` blocks
- skills, MCP access, tool behavior, or disabled agents
- background orchestration, session reuse, multiplexer panes, `/loop`, or DeepWork
- recurring workflow friction that a prompt/config change can solve

Use it proactively only with restraint. If the user repeatedly asks for the
same rule, suggest adding it to a project-local prompt/config first.

## Project-Local Customization Is First-Class

Use project files for project-specific behavior. Use user files only for global
defaults that should affect every project.

| Path | Use |
|---|---|
| `<project>/.opencode/oh-my-opencode-slim.jsonc` | Project plugin config with comments/trailing commas |
| `<project>/.opencode/oh-my-opencode-slim.json` | Project plugin config as strict JSON |
| `~/.config/opencode/oh-my-opencode-slim.jsonc` | User plugin config with comments; takes precedence over user `.json` |
| `~/.config/opencode/oh-my-opencode-slim.json` | User plugin config, often generated from `model-profile.jsonc` |
| `~/.config/opencode/opencode.json` | OpenCode core config: plugin registration, providers, MCPs, permissions |
| `.opencode/loop-history/` | Local `/loop` history/state; normally keep uncommitted |

Prompt override files can exist at both project and user scope:

| Path | Use |
|---|---|
| `.opencode/oh-my-opencode-slim/{agent}.md` | Project full prompt replacement |
| `.opencode/oh-my-opencode-slim/{agent}_append.md` | Project append-only prompt tuning |
| `.opencode/oh-my-opencode-slim/{preset}/{agent}.md` | Project preset-specific replacement |
| `.opencode/oh-my-opencode-slim/{preset}/{agent}_append.md` | Project preset-specific append |
| `~/.config/opencode/oh-my-opencode-slim/{agent}.md` | User full prompt replacement |
| `~/.config/opencode/oh-my-opencode-slim/{agent}_append.md` | User append-only prompt tuning |
| `~/.config/opencode/oh-my-opencode-slim/{preset}/{agent}.md` | User preset-specific replacement |
| `~/.config/opencode/oh-my-opencode-slim/{preset}/{agent}_append.md` | User preset-specific append |

Built-in prompt file names are exact agent names:
`orchestrator`, `oracle`, `librarian`, `explorer`, `designer`, `fixer`,
`observer`, and `council`.

Prefer `{agent}_append.md` for small behavior tuning. Use `{agent}.md` only
when the user intentionally wants to replace the bundled prompt entirely.

## Prompt Lookup Order

When a preset is active, prompt files resolve in this order:

1. Project preset directory: `.opencode/oh-my-opencode-slim/{preset}/`
2. Project root directory: `.opencode/oh-my-opencode-slim/`
3. User preset directory: `~/.config/opencode/oh-my-opencode-slim/{preset}/`
4. User root directory: `~/.config/opencode/oh-my-opencode-slim/`
5. Built-in plugin prompt from the package

At each location, `{agent}.md` is a full replacement and
`{agent}_append.md` appends to the selected base prompt.

## v2.1.0 Merge Rules

- Project config is loaded automatically at startup; no generator is needed.
- Project `preset` selects the active preset for that project.
- Project `presets` now deep-merge with user presets. You may override a single
  field under `presets.<preset>.<agent>` without copying the whole preset.
- Nested object overrides merge where the plugin schema supports them.
- Arrays replace when set. Top-level arrays such as `disabled_agents` and
  `disabled_mcps` do not concatenate; list the complete desired value.
- Agent-level arrays such as `skills`, `mcps`, and model fallback lists also
  replace when explicitly overridden.
- Deep-merge cannot unset inherited nested keys; choose a replacement value or
  override at the narrowest useful level.

Minimal project override:

```jsonc
{
  "preset": "openai",
  "presets": {
    "openai": {
      "fixer": {
        "model": "openai/gpt-5.6-sol",
        "variant": "xhigh",
        "temperature": 0.8
      }
    }
  }
}
```

Cross-preset built-in override:

```jsonc
{
  "agents": {
    "librarian": {
      "skills": [],
      "mcps": ["web-search-prime", "context7"]
    }
  }
}
```

## v2.1.1 Features

- **Council fallback chains**: a councillor's `model` field now accepts an array
  for ordered fallback. Entries may be plain model ID strings or `{ "id", "variant" }`
  objects. The chain runs top-to-bottom; the first model that succeeds is used.
- **`fallback.maxRetries`** (default `3`): number of consecutive rate-limit
  responses before the chain aborts or swaps to the next model.
- **`fallback.runtimeOverride`** (default `true`): whether an out-of-chain
  `/model` pick still triggers the fallback chain on failure.
- **`compactSidebar`** now defaults to `true`: the agent sidebar renders
  compactly out of the box; set it `false` to restore the old spacing.

Configure runtime fallback behavior under the top-level `fallback` object.
Configure a councillor's ordered fallback chain in that councillor's `model`
array; there is no per-councillor `fallback` object.

### GPT-5.6 reasoning and OAuth limits

- OpenAI hides raw chain-of-thought by design. OpenCode already requests
  reasoning summaries and encrypted multi-turn continuity; do not duplicate
  those options in agent config.
- OpenCode 1.17.18 does not generate GPT-5.6's `max` variant. Define `max` in
  the model's `variants` and keep fallback effort in model-level `options` so
  cross-provider agent fallback arrays do not leak OpenAI-specific settings.
- OpenCode 1.17.18 advertises GPT-5.6's larger direct-API context, but the Codex
  OAuth backend accepts less. Until
  [issue #36247](https://github.com/anomalyco/opencode/issues/36247) is fixed,
  set each local GPT-5.6 model's `limit` to `context: 500000`, `input: 372000`,
  and `output: 128000`. These explicit limits restore automatic compaction;
  manually compact before roughly 350K input only as a backstop.
- Do not use GPT-5.6 `*-pro` aliases on OpenCode 1.17.18: the bundled SDK does
  not serialize `reasoning.mode`. Sol with `max` is the strongest reliable
  quality-first route; keep `max` on the normal AI-SDK runtime.

## Common Customizations

- **Switch presets**: choose which generated or custom preset is active.
- **Tune models**: assign different models/variants per agent.
- **Limit costs**: use cheaper models for `explorer`, `librarian`, and `fixer`.
- **Improve quality**: use stronger models for `orchestrator`, `oracle`, or
  design-heavy `designer` work.
- **Control skills**: set `skills` per agent with `["*"]`, explicit names, or
  exclusions like `["*", "!codemap"]`.
- **Control MCPs**: set `mcps` per agent with the same allow/exclude style.
- **Enable optional agents**: remove agents from `disabled_agents` and configure
  an appropriate model, such as a vision-capable `observer`.
- **Add custom agents**: define focused specialists under `agents.<name>`.
- **Tune prompts**: override or extend prompts for project or user workflow
  preferences.
- **Guide delegation**: add `orchestratorPrompt` for custom agents so the
  Orchestrator knows when to call them and when not to.

## Schema Boundaries

- Built-in agents (`orchestrator`, `oracle`, `librarian`, `explorer`,
  `designer`, `fixer`, `observer`, `council`) can set models, variants, skills,
  MCPs, options, and display names in config.
- Built-in agent `prompt` and `orchestratorPrompt` fields are not supported in
  `oh-my-opencode-slim.json[c]`; use markdown prompt files instead.
- Unknown keys under top-level `agents` are custom agents. Custom agents may use
  `prompt` and `orchestratorPrompt` directly in config.

## Custom Agent Pattern

Custom agents work best when they are narrow, repeatable, and easy to route.
Constrain `skills` and `mcps` explicitly, often to `[]`, and rely on the
runtime permission scaffolding derived from those fields. Do not add a new
`permissions`/`permission` field for custom agents.

```jsonc
{
  "agents": {
    "api-reviewer": {
      "model": "openai/gpt-5.6-sol",
      "variant": "high",
      "prompt": "You review API design, compatibility, error semantics, and migration risk. Return concise findings with file references.",
      "orchestratorPrompt": "Delegate to @api-reviewer for API contract changes, public SDK changes, backwards-compatibility questions, or migration-risk review. Do not use it for routine implementation.",
      "skills": [],
      "mcps": []
    }
  }
}
```

Good custom agents have:

- a specific job;
- clear trigger and non-use conditions in `orchestratorPrompt`;
- only the skills and MCPs they actually need;
- a model appropriate to the task's judgment/cost needs.

Avoid duplicating existing specialists:

- codebase scouting → `explorer`
- external docs/research → `librarian`
- architecture/debugging/review → `oracle`
- UI/UX polish → `designer`
- scoped mechanical implementation → `fixer`

## Loops and Multi-Phase Work

- Use the official `/loop` command for quick user-facing execute/verify loops.
- Keep `.opencode/loop-history/` local; it should normally stay uncommitted.
- Prefer DeepWork for broad, risky, or multi-phase work that needs a persistent
  plan and verification gates.
- Do not replace `/loop` or DeepWork with ad hoc prompt machinery unless the
  user explicitly asks for plugin development.

## Safe Improvement Rules

Configuration changes affect future agent behavior, so treat them as user-owned.

1. Ask before changing config or prompts unless the user explicitly requested
   the exact edit.
2. Prefer project-local files for project-only behavior.
3. Prefer narrow changes; do not rewrite prompts when an append rule solves it.
4. Preserve existing settings and comments where practical.
5. Mention cost, permission, or delegation changes before applying them.
6. Tell the user whether OpenCode needs a restart or next run to apply changes.

## Configuration Workflow

When making or proposing changes:

1. Inspect the active user and project config files.
2. Identify active `preset` and relevant agent blocks.
3. Choose the smallest useful config or prompt change.
4. Ask for confirmation unless already explicitly authorized.
5. Apply the edit carefully and preserve unrelated settings.
6. Validate that JSON/JSONC remains parseable or run the available config check.
7. Explain activation: "This should apply on the next OpenCode run; restart
   OpenCode if you need it immediately."

## Prompt Tuning Pattern

Prompt edits are best for recurring behavior that should happen across many
sessions.

Good reasons to tune a prompt:

- The Orchestrator repeatedly delegates too much or too little.
- A specialist repeatedly misses a project-specific convention.
- The user wants a stable communication or verification style.
- The team has a recurring review checklist or deployment rule.

Poor reasons to tune a prompt:

- A one-off task failed once.
- Normal session instructions solve the current problem.
- The change would make the agent worse for general use.

When suggesting a prompt improvement, say:

```text
I noticed this is recurring. I can add a small rule to <agent/config path> so
future runs handle it automatically. Want me to make that config change?
```

## Final Checklist

- [ ] Did the user confirm config/prompt edits, unless explicitly requested?
- [ ] Did the edit preserve existing settings?
- [ ] Is the active preset still valid?
- [ ] Are skill/MCP/tool permissions intentional and minimal?
- [ ] Did you mention OpenCode restart/next-run behavior?
