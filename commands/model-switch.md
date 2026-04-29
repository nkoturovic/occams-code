---
description: Switch which model runs which agent role (global or per-project)
---

> ⚠️ Only make changes the user explicitly requests. Don't suggest models unless asked.

## Finding the Right Model ID & Temperature

Before editing, find the correct values:

1. **Model IDs** — Read `~/.config/opencode/model-profile.jsonc`. Copy the exact `"model"` string from the same agent in another preset (e.g., if user wants Claude Sonnet for oracle, check `model-profile.jsonc` — it's already there for `balanced.oracle`).
2. **Temperatures** — Read `~/wiki/wiki/concepts/agent-roles-and-models.md` (temperature table near line 96). For Kimi: no temp, set `"thinking": 16000`. For DeepSeek V4 Pro: no temp. For others: use the table value.
3. **Provider models** — `~/.config/opencode/opencode.json` lists all valid model IDs per provider. Use exact IDs from here.

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

