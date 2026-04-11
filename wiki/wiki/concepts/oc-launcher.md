---
summary: "oc launcher boot sequence, session modes, permission system, and smart prompts"
type: concept
tags: [occams-code, opencode, launcher, bin-oc]
sources: []
related:
  - occams-code-setup
  - troubleshooting
created: 2026-04-10
updated: 2026-04-10
confidence: high
---

# The `oc` Launcher

## Boot Sequence

When you run `oc`, the following happens in order:

```
1. Dependency checks     → jq, fzf, python3, config file (fail fast)
2. Bash version gate     → requires 4.0+ (macOS default is 3.2, needs brew bash)
3. Smart memory prompts  → detect-project-state.py checks wiki state
4. Session choice        → new or continue last session
5. [New only] Provider health  → pings APIs in parallel (~3s)
6. [New only] Preset select    → interactive fzf or --preset flag
7. [New only] Agent tweaks     → role-picker.py with role-aware sorting (optional)
8. [New only] AGENTS.md sync   → sync-agents-md.py keeps model table current
9. Permission setup      → --safe or --unsafe modifies opencode.json
10. Launch               → exec opencode (replaces shell process)
```

## Session Modes

| Command | Behavior |
|---------|----------|
| `oc` | Full interactive: session choice → preset → tweaks → launch |
| `oc -c` | Continue last session (skips preset/tweaks, still runs memory prompts) |
| `oc --quick` | Pick preset only, skip agent tweaking |
| `oc --preset <name>` | Direct preset, skip session/preset prompts |
| `oc --safe` | Enable permission prompts for this session |
| `oc --unsafe` | Auto-approve all permissions for this session |

**Continue sessions** (`oc -c`) skip preset selection and agent tweaking but still run memory prompts — wiki state is always checked.

## Permission System

`--safe` and `--unsafe` are mutually exclusive session-level overrides:

1. `bin/oc` saves current `opencode.json` permission state to a temp file
2. Modifies the `"permission"` key: `"allow"` (unsafe) or removes it (safe)
3. Sets a shell `trap` to restore original state on EXIT/INT/TERM
4. Launches OpenCode
5. Restores original config when OpenCode exits

**Edge case:** If OpenCode is killed with SIGKILL (system kill -9, OOM), the trap doesn't fire. On next launch, `oc` auto-detects the leftover backup file and recovers the original permission state.

**Default:** The generated `opencode.json` includes `"permission": "allow"` — so launching without flags is equivalent to `--unsafe`.

## Smart Prompts (during boot)

`detect-project-state.py` outputs shell variables that drive interactive prompts:

| Condition | Prompt |
|-----------|--------|
| No wiki page for project | "Initialize project wiki memory now?" |
| No project AGENTS.md | "No project AGENTS.md found. Create it?" |

All prompts are optional — the user can decline and still launch.

## Utility Commands

| Command | What it does |
|---------|-------------|
| `oc --doctor` | Integration health checks (models, AGENTS.md, wiki, providers) |
| `oc --sync-config` | Regenerate AGENTS.md model table from config |
| `oc --init-project` | Create wiki page + project AGENTS.md |
| `oc --ingest-repo owner/repo` | Snapshot GitHub repo into wiki raw/repos/ |
| `oc --lint-wiki` | Run wiki content health check (dead links, orphans, stale pages) |

## Bash Version Gate

`bin/oc` requires bash 4.0+ because it uses `${var,,}` (lowercase) and `${arr[@]+"${arr[@]}"}` (empty array handling). macOS ships bash 3.2.

**Fix:** `brew install bash` and either:
- Run installer with `/opt/homebrew/bin/bash scripts/install.sh`
- Change login shell: `chsh -s /opt/homebrew/bin/bash`
- Or run oc with: `/opt/homebrew/bin/bash ~/.config/opencode/bin/oc`

## Related
- [[occams-code-setup]] — Config files, scripts inventory
- [[troubleshooting]] — What to do when things fail
