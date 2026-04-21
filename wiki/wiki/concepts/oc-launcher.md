---
summary: "oc launcher boot sequence, session modes, permission system, and smart prompts"
type: concept
tags: [occams-code, opencode, launcher, bin-oc]
sources: []
related:
  - occams-code-setup
  - troubleshooting
created: 2026-04-10
updated: 2026-04-21
confidence: high
---

# The `oc` Launcher

## Boot Sequence

When you run `oc`, the following happens in order:

```
1. Bash version gate     → requires 4.0+ (fail fast)
2. Dependency checks     → jq, config file
3. Arg parse + validate  → --safe/--unsafe mutual exclusion checked here
4. Standalone commands   → --doctor, --ingest-repo, --init-project (skip everything, exit)
5. Crash recovery        → clean up stale permission backups (glob cleanup, PID-based names)
6. --preset flag         → merge into project config (jq, preserves existing fields)
7. First-run setup       → create project config if missing (interactive only)
8. Banner + config       → only shown if interactive AND not --quick
9. Session choice        → new or continue (default: continue [2])
10. Launch               → exec opencode (or permission wrapper for --safe/--unsafe)
```

## Session Modes

| Command | Behavior |
|---------|----------|
| `oc` | Interactive: preset check → session choice → launch |
| `oc -c` | Continue last session (skips session choice) |
| `oc --quick` | Skip all output and prompts, just launch |
| `oc --preset <name>` | Merge preset into project config, launch |
| `oc --safe` / `oc --unsafe` | Permission override for this session |

**Continue** is the default session choice (just press Enter).

## Permission System

`--safe` and `--unsafe` are mutually exclusive session-level overrides:

1. `bin/oc` saves current `opencode.json` permission state to a temp file
2. Modifies the `"permission"` key: `"allow"` (unsafe) or removes it (safe)
3. Sets a shell `trap` to restore original state on EXIT/INT/TERM
4. Launches OpenCode
5. Restores original config when OpenCode exits

**Edge case:** If OpenCode is killed with SIGKILL (system kill -9, OOM), the trap doesn't fire. On next launch, `oc` auto-detects leftover backup files and recovers the original permission state.

Backup filename is `/tmp/oc-perm-backup-UID-PID` — the PID suffix prevents concurrent sessions from corrupting each other's backups. Crash recovery globs all stale backups (`/tmp/oc-perm-backup-UID-*`).

**Default:** The generated `opencode.json` includes `"permission": "allow"` — so launching without flags is equivalent to `--unsafe`.

## Per-Project Config

On first `oc` in a new project, the launcher offers to create `.opencode/oh-my-opencode-slim.json` with a preset choice. The plugin reads this file natively and deep-merges it with the global config.

Edit the file directly to override preset or individual agent models. No wizard needed.

`--preset` merges into existing project config (preserves custom model overrides).

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
