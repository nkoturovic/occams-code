---
description: Switch which model runs which agent role (global or per-project)
---

> ⚠️ Only make changes the user explicitly requests. Don't suggest models unless asked.

## Quick Reference: Model IDs & Temperatures

Use these exact model IDs and temperature values when the user picks a model:

| Model | Model ID (in config) | Temperature | Thinking |
|-------|---------------------|-------------|----------|
| DeepSeek V4 Pro | `deepseek/deepseek-v4-pro` | **Skip (auto)** | Auto (`@ai-sdk/deepseek`) |
| DeepSeek V3.2 | `deepseek/deepseek-v3.2` or `openrouter/deepseek/deepseek-v3.2` | 0.1–0.2 | No |
| Kimi K2.6 | `kimi-for-coding/kimi-for-coding` | **Skip (API enforced)** | `"thinking": 16000` |
| GLM-5.1 (Z.AI) | `zai-coding-plan/glm-5.1` | 0.3–0.6 | No |
| Claude Opus 4 | `anthropic/claude-opus-4-6` (live) or `openrouter/anthropic/claude-opus-4.6` (repo) | 0.3 | No |
| Claude Sonnet 4 | `anthropic/claude-sonnet-4-6` (live) or `openrouter/anthropic/claude-sonnet-4.6` (repo) | 0.1–0.2 | No |
| Gemini 3.1 Pro | `openrouter/google/gemini-3.1-pro-preview` | 1.0 | No |
| Gemini 3 Flash | `openrouter/google/gemini-3-flash-preview` | 1.0 | No |
| Qwen 3.6 Plus | `openrouter/qwen/qwen3.6-plus` | 0.6 | No |
| Qwen 3 Coder | `openrouter/qwen/qwen3-coder` | 1.0 | No |
| Nemotron Free | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 1.0 | No |

For exact per-preset values, read the current `model-profile.jsonc`.

## Global model switch (applies everywhere)

Valid presets: `custom`, `balanced`, `premium`, `cheap`.  
Valid agents: `orchestrator`, `oracle`, `designer`, `explorer`, `librarian`, `fixer`, `observer`.

1. **Read** `~/.config/opencode/oh-my-opencode-slim.json` to see current state.
2. **Edit** `~/.config/opencode/model-profile.jsonc` — change `model` and `temperature`/`thinking` for the target agent in the target preset using values from the reference table above.
3. **Run** the generator:

```bash
python3 ~/.config/opencode/scripts/model-profile.py \
  ~/.config/opencode/model-profile.jsonc \
  ~/.config/opencode/oh-my-opencode-slim.json
```

4. Tell the user to restart OpenCode.

## Per-project model switch (this project only)

Edit `~/.config/opencode/.opencode/oh-my-opencode-slim.jsonc`. Only specify the roles to override:

```jsonc
{"presets":{"custom":{"explorer":{"model":"openrouter/qwen/qwen3.6-plus","variant":"high"}}}}
```

No generator needed — omo-slim reads this file automatically at startup. Restart after saving.

Docs: `~/wiki/wiki/concepts/model-profile-guide.md`

