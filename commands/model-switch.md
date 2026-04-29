---
description: Switch which model runs which agent role (global or per-project)
---

> ⚠️ Only make changes the user explicitly requests. Don't suggest models unless asked.

## Finding the Right Model ID & Temperature

Both come from one file: `~/.config/opencode/model-profile.jsonc`.

Every model in your config already has a temperature example in at least one preset. To find the right value for a model:
1. Search for that model string across all presets in `model-profile.jsonc`
2. Copy its `"temperature"` or `"thinking"` field — same model, same temp regardless of role

Rules (for models not yet in config):
- Kimi models → no temperature, set `"thinking"`: 16000
- DeepSeek V4 Pro → no temperature, no thinking (provider handles it)
- All other models → 1.0 unless you have a specific reason to lower it

## Global model switch (applies everywhere)

Valid presets: `custom`, `balanced`, `premium`, `cheap`.  
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
{"presets":{"custom":{"explorer":{"model":"openrouter/qwen/qwen3.6-plus","variant":"high"}}}}
```

No generator needed — omo-slim reads this at startup. Restart after saving.

Docs: `~/wiki/wiki/concepts/model-profile-guide.md`

