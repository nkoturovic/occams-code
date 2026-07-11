---
description: Switch which model runs which agent role (global or per-project)
---

> ⚠️ Only make changes the user explicitly requests. Don't suggest models unless asked.

## Finding the Right Model ID & Temperature

Both come from one file: `~/.config/opencode/model-profile.jsonc`.

Every model in your config already has a temperature example in at least one preset. To find the right value for a model:
1. Search for that model string across all presets in `model-profile.jsonc`
2. Copy its `"temperature"` field — same model, same temp regardless of role

Temperature is always set explicitly for every agent. For thinking-mode models
(Kimi, DeepSeek V4 Pro), the API ignores temperature — use these values for
consistency with the plugin defaults:
- DeepSeek V4 Pro: 0.8 (explorer), 1.0 (council)
- Kimi K2.7 Code: 1.0 (API-locked — `temperature: false` in config)
- GLM 5.2: 0.8 (orchestrator/librarian/fixer)
- Claude: 0.6 (premium preset)
- All other models: 1.0 unless you have a specific reason to lower it

## Global model switch (applies everywhere)

Valid presets: `balanced`, `cheap`, `deepseek`, `premium`, `custom`, `openai`, `openai-fast`.
Valid agents: `orchestrator`, `oracle`, `designer`, `explorer`, `librarian`, `fixer`, `observer`.

`openai-fast` is the opt-in ChatGPT OAuth Fast/Priority sibling of `openai`; model roles, capabilities, reasoning, fallbacks, and council stay identical.

1. **Edit** `~/.config/opencode/model-profile.jsonc` — change `model` and `temperature` for the target agent in the target preset using values found above.
2. **Run** the generator:

```bash
python3 ~/.config/opencode/scripts/model-profile.py \
  ~/.config/opencode/model-profile.jsonc \
  ~/.config/opencode/oh-my-opencode-slim.json
```

3. Tell the user to restart OpenCode.

## Per-project model switch (this project only)

Edit `.opencode/oh-my-opencode-slim.jsonc`. In v2.1.0, project config deep-merges with the user config, so only specify the roles/fields to override. Arrays replace when set.

```jsonc
{"agents":{"explorer":{"model":"openrouter/google/gemini-3.5-flash","temperature":1.0}}}
```

No generator needed — omo-slim reads this at startup. Restart after saving.

Docs: `~/.agents/wiki/concepts/model-profile-guide.md`
