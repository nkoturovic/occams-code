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
1. Dependency checks     → jq, config file (fail fast)
2. Bash version gate     → requires 4.0+ (macOS default is 3.2, needs brew bash)
3. Crash recovery        → recover permissions from previous crash if backup exists
4. Standalone commands   → --doctor, --ingest-repo, --init-project (exit early)
5. Preset select         → --preset flag or first-run fzf prompt
6. Show config           → display active preset and agent models
7. Session choice        → new or continue last session (skip if --quick/--preset)
8. First-run setup       → create project config if missing
9. Launch                → exec opencode (replaces shell process)
```

## Session Modes

| Command | Behavior |
|---------|----------|
| `oc` | Full interactive: session choice → preset → launch |
| `oc -c` | Continue last session (skips preset selection) |
| `oc --quick` | Skip prompts, use project/global config directly |
| `oc --preset <name>` | Set preset, create project config, launch |
| `oc --safe` | Enable permission prompts for this session |
| `oc --unsafe` | Auto-approve all permissions for this session |

**Continue sessions** (`oc -c`) skip preset selection but still show config.

## Permission System

`--safe` and `--unsafe` are mutually exclusive session-level overrides:

1. `bin/oc` saves current `opencode.json` permission state to a temp file
2. Modifies the `"permission"` key: `"allow"` (unsafe) or removes it (safe)
3. Sets a shell `trap` to restore original state on EXIT/INT/TERM
4. Launches OpenCode
5. Restores original config when OpenCode exits

**Edge case:** If OpenCode is killed with SIGKILL (system kill -9, OOM), the trap doesn't fire. On next launch, `oc` auto-detects the leftover backup file and recovers the original permission state.

**Default:** The generated `opencode.json` includes `"permission": "allow"` — so launching without flags is equivalent to `--unsafe`.

## Per-Project Config

On first `oc` in a new project, the launcher offers to create `.opencode/oh-my-opencode-slim.json` with a preset choice. The plugin reads this file natively and deep-merges it with the global config.

Edit the file directly to override preset or individual agent models. No wizard needed.

## Utility Commands

| Command | What it does |
|---------|-------------|
| `oc --doctor` | Diagnostics (config validity, wiki structure, wiki lint) |
| `oc --init-project` | Create wiki page + project AGENTS.md |
| `oc --ingest-repo owner/repo` | Snapshot GitHub repo into wiki raw/repos/ |

## Bash Version Gate

`bin/oc` requires bash 4.0+ because it uses `${var,,}` (lowercase) and `${arr[@]+"${arr[@]}"}` (empty array handling). macOS ships bash 3.2.

**Fix:** `brew install bash` and either:
- Run installer with `/opt/homebrew/bin/bash scripts/install.sh`
- Change login shell: `chsh -s /opt/homebrew/bin/bash`
- Or run oc with: `/opt/homebrew/bin/bash ~/.config/opencode/bin/oc`

## Related
- [[occams-code-setup]] — Config files, scripts inventory
- [[troubleshooting]] — What to do when things fail
