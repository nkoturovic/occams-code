---
description: Show permission modes and how to use --safe / --unsafe
---
Explain the permission system for this setup:

- **Default:** `"permission": "allow"` in opencode.json — auto-approve. We're not scared of our own agents.
- `oc --safe` — temporarily enables permission prompts for this session (restores config on exit).
- `oc --unsafe` — temporarily auto-approves everything for this session (if you changed default to prompts).
- `--safe` and `--unsafe` are mutually exclusive.

To change the permanent default, edit `~/.config/opencode/opencode.json`:
- Remove `"permission": "allow"` → prompts become default
- Add `"permission": "allow"` → auto-approve becomes default

```bash
oc --safe              # prompts for this session only
oc --unsafe            # auto-approve for this session only
oc                     # uses your configured default
```

$ARGUMENTS
