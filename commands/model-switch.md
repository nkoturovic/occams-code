---
description: Switch which model runs which agent role
---

To change a model for an agent role (e.g., swap orchestrator to a different model):

1. Edit `/home/kotur/.config/opencode/model-profile.jsonc` — change the `model` field for the agent in the appropriate preset
2. Run the generator:
   ```bash
   python3 /home/kotur/.config/opencode/scripts/model-profile.py /home/kotur/.config/opencode/model-profile.jsonc /home/kotur/.config/opencode/oh-my-opencode-slim.json
   ```
3. Tell the user to restart OpenCode for changes to take effect

Temperature rules (the generator handles these automatically):
- Kimi models: skip temperature (API enforces), set `"thinking": 16000`
- DeepSeek V4 Pro: skip temperature (thinking mode auto)
- All other models: set `"temperature"` field

See `/home/kotur/wiki/wiki/concepts/model-profile-guide.md` for docs.
