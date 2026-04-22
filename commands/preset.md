---
description: Show active preset and agent models
---
1. Run this bash command to show the current preset and models (checks project config first, then global):

```bash
python3 -c "
import json
from pathlib import Path

proj = Path('.opencode/oh-my-opencode-slim.json')
cfg = json.loads(Path.home().joinpath('.config/opencode/oh-my-opencode-slim.json').read_text())
source, preset = 'global', cfg['preset']
if proj.exists():
    pc = json.loads(proj.read_text())
    if 'preset' in pc:
        preset, source = pc['preset'], 'project'

agents = cfg['presets'][preset]
print(f'Active: {preset} ({source})')
for a, c in agents.items():
    print(f'  {a}: {c[\"model\"]}')
print(f'Available: {\", \".join(cfg[\"presets\"].keys())}')
print('Switch: oc --preset <name>')
"
```

$ARGUMENTS
