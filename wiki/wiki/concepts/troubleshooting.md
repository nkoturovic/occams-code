---
summary: "Common failure modes, diagnostic commands, known-bad models, and fixes for Occam's Code"
type: concept
tags: [occams-code, opencode, troubleshooting, debugging]
sources: []
related:
  - occams-code-setup
  - oc-launcher
  - agent-roles-and-models
created: 2026-04-10
updated: 2026-04-10
confidence: high
---

# Troubleshooting

## Quick Diagnostics

| Problem | Run this |
|---------|----------|
| Agents not working | `oc --doctor` |
| Model different from expected | Check if fallback activated (60s timeout) |
| AGENTS.md model table stale | `oc --sync-config` |
| Provider dead or credits low | `python3 ~/.config/opencode/scripts/provider-health.py` |
| Wiki not being used by agent | Check AGENTS.md reads index.md on start. Run `/wiki` to verify. `oc --doctor` checks wiki structure and freshness |
| Wiki has dead links or orphans | `oc --lint-wiki` or `python3 ~/.config/opencode/scripts/wiki-lint.py` |
| Config not found | Verify `oh-my-opencode-slim.json` exists in `~/.config/opencode/` |
| Permission state stuck | Check `opencode.json` for `"permission": "allow"` |

## Common Failure Modes

### Model different from configured
**Cause:** Fallback chain activated (primary model timed out) or auto-repair changed it.
**How to check:** Run `model-optimizer.py --validate` to see current state.
**Fix:** If primary is valid, the timeout may be too short for complex tasks. The chain falls back gracefully — this is expected behavior.

### "bash version too old"
**Cause:** macOS ships bash 3.2. `bin/oc` requires 4.0+.
**Fix:** `brew install bash`, then use `/opt/homebrew/bin/bash` explicitly or change login shell.

### AGENTS.md model table drifts from config
**Cause:** Config was edited but AGENTS.md not regenerated.
**Fix:** `oc --sync-config` or `python3 ~/.config/opencode/scripts/sync-agents-md.py`.

### Permission stuck in unsafe mode
**Cause:** OpenCode crashed hard (SIGKILL), shell trap didn't fire to restore config. On next launch, `oc` auto-recovers from the crash backup.
**Fix:** The recovery is automatic. If permissions still seem wrong, edit `opencode.json` and remove `"permission": "allow"`.

### Provider returns credit errors
**Cause:** OpenRouter credit depleted. Credit errors come as response content, not HTTP errors — fallback plugin may not detect them.
**Fix:** Check balance: `python3 ~/.config/opencode/scripts/provider-health.py`. Top up at openrouter.ai/keys.

### Fallback timeout too short
**Cause:** Complex tasks (especially oracle/opus) can exceed 60s.
**Fix:** 60s is the configured default. This is a known trade-off — shorter timeout = faster fallback to working models, but may abort a slow-but-correct response.

### Known-bad models
Some models validate in the catalog but fail at runtime. `model-optimizer.py` maintains a `KNOWN_BAD_MODELS` list and auto-repairs on startup.

### Models not loading after provider change
**Fix:** `opencode models --refresh` to rebuild the model cache.

### Wiki pages stale
**Cause:** Project has new commits since last wiki update.
**Fix:** `oc --lint-wiki` to detect staleness. Update wiki pages manually or `/remember` to save new discoveries.

## When Things Break Badly

### Nuclear reset
1. Back up `oh-my-opencode-slim.json` and `opencode.json`
2. Reinstall: `bunx oh-my-opencode-slim@latest install --reset`
3. Copy your preset config back into the new file
4. Run `oc --doctor` to verify

### Config file locations
```
~/.config/opencode/opencode.json              # Core config (generated)
~/.config/opencode/oh-my-opencode-slim.json   # Plugin config (your presets)
~/.config/opencode/AGENTS.md                  # Agent instructions
~/.config/opencode/bin/oc                     # Launcher script
~/.config/opencode/scripts/                   # 9 utility scripts
~/.config/opencode/commands/                  # 5 slash command docs
~/.config/opencode/auth.json                  # API keys (NEVER share)
```

## Related
- [[occams-code-setup]] — Architecture and config structure
- [[oc-launcher]] — Boot sequence and session modes
- [[agent-roles-and-models]] — Model selection rationale
