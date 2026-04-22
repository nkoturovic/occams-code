---
description: Show or switch active preset and agent models
---
1. Run this bash command with the user's argument (if any):

```bash
python3 -c "
import json, sys
from pathlib import Path

cfg_path = Path.home() / '.config/opencode/oh-my-opencode-slim.json'
cfg = json.loads(cfg_path.read_text())
available = list(cfg['presets'].keys())
arg = '$ARGUMENTS'.strip()

if not arg:
    # Show current preset
    proj = Path('.opencode/oh-my-opencode-slim.json')
    source, preset = 'global', cfg['preset']
    if proj.exists():
        pc = json.loads(proj.read_text())
        if 'preset' in pc:
            preset, source = pc['preset'], 'project'
    agents = cfg['presets'][preset]
    print(f'Active: {preset} ({source})')
    for a, c in agents.items():
        print(f'  {a}: {c[\"model\"]}')
    print(f'Available: {\", \".join(available)}')
    print('Switch: /preset <name>  (next session)')
else:
    if arg not in available:
        print(f'Unknown: {arg}')
        print(f'Available: {\", \".join(available)}')
        sys.exit(1)
    proj = Path('.opencode/oh-my-opencode-slim.json')
    pc = json.loads(proj.read_text()) if proj.exists() else {}
    pc['preset'] = arg
    proj.parent.mkdir(parents=True, exist_ok=True)
    proj.write_text(json.dumps(pc, indent=2) + chr(10))
    print(f'Switched to: {arg} (restart session to apply)')
"
```

If $ARGUMENTS was provided and succeeded, remind the user to restart the session.
