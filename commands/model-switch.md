---
description: Switch which model runs which agent role (global or per-project)
---

> ⚠️ Only make changes the user explicitly requests. Don't suggest models unless asked.

## Finding the Right Model ID & Temperature

Both come from one file: `~/.config/opencode/model-profile.jsonc`.

Every model in your config already has a temperature example in at least one preset. To find the right value for a model:
1. Search for that model string across all presets in `model-profile.jsonc`
2. Copy its `"temperature"` or `"thinking"` field — same model, same temp regardless of role

Temperature is always set explicitly for every agent. For thinking-mode models
(Kimi, DeepSeek V4 Pro), the API ignores temperature — use these values for
consistency with the plugin defaults:
- DeepSeek V4 Pro: 0.3 (orchestrator), 0.1 (oracle/fixer/observer)
- Kimi K2.6: 0.7 (designer), 0.1 (fixer/observer)
- GLM 5.1: 0.3–0.6 (tested — avoid 0.0, it breaks reasoning)
- Claude: 0.1–0.3 (fixer/oracle), 0.3 (orchestrator)
- All other models: 1.0 unless you have a specific reason to lower it

Kimi models additionally require `"thinking"`: 32000 (or 16000 for minimum).

## Global model switch (applies everywhere)

Valid presets: `balanced`, `cheap`, `deepseek`, `premium`, `custom`, `openai`.  
Valid agents: `orchestrator`, `oracle`, `designer`, `explorer`, `librarian`, `fixer`, `observer`.

1. **Edit** `~/.config/opencode/model-profile.jsonc` — change `model` and `temperature`/`thinking` for the target agent in the target preset using values found above.
2. **Run** the generator:

```bash
python3 ~/.config/opencode/scripts/model-profile.py \
  ~/.config/opencode/model-profile.jsonc \
  ~/.config/opencode/oh-my-opencode-slim.json
```

3. Tell the user to restart OpenCode.

## Per-project model switch (this project only)

Edit `.opencode/oh-my-opencode-slim.jsonc`. Only specify the roles to override:

```jsonc
{"agents":{"explorer":{"model":"openrouter/qwen/qwen3.6-plus","variant":"high","temperature":0.7}}}
```

No generator needed — omo-slim reads this at startup. Restart after saving.

Docs: `~/.agents/wiki/concepts/model-profile-guide.md`
