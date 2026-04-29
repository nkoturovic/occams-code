---
description: Switch which model runs which agent role
---

When the user asks to change a model for a specific agent role in a specific preset:

1. **Read** `~/.config/opencode/oh-my-opencode-slim.json` to see current assignments (JSON — Read tool works directly).
   Valid presets: `custom`, `balanced`, `premium`, `cheap`.
   Valid agents: `orchestrator`, `oracle`, `designer`, `explorer`, `librarian`, `fixer`, `observer`.

2. **Edit** `~/.config/opencode/model-profile.jsonc` — change only the `model` field for the target agent in the target preset. Don't modify comments; only edit JSON values. For Kimi models, set `"thinking": 16000` (no temperature). For DeepSeek V4 Pro, skip both. For all other models, set `"temperature"` to the vendor-recommended value (ask the user if unsure).

3. **Run** the generator to confirm the change works:

```bash
python3 ~/.config/opencode/scripts/model-profile.py \
  ~/.config/opencode/model-profile.jsonc \
  ~/.config/opencode/oh-my-opencode-slim.json
```

4. Tell the user to restart OpenCode for the change to take effect.

See `~/wiki/wiki/concepts/model-profile-guide.md` for docs.
