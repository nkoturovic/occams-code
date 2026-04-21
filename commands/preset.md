---
description: Show active preset and agent models
---
1. Run this bash command to show the current preset and models (checks project config first, then global):

```bash
python3 -c "
import json
from pathlib import Path

# Check project config first
project_cfg = Path('.opencode/oh-my-opencode-slim.json')
global_cfg = Path.home() / '.config/opencode/oh-my-opencode-slim.json'
source = 'global'
preset = None

if project_cfg.exists():
    pcfg = json.loads(project_cfg.read_text())
    if 'preset' in pcfg:
        preset = pcfg['preset']
        source = 'project'

cfg = json.loads(global_cfg.read_text())
if preset is None:
    preset = cfg['preset']

agents = cfg['presets'][preset]
print(f'Active preset: {preset} ({source})')
print()
for agent, conf in agents.items():
    print(f'  {agent}: {conf[\"model\"]}')
print()
print(f'Available: {\", \".join(cfg[\"presets\"].keys())}')
"
```

2. Then ask the user if they want to switch to a different preset. Note: switching takes effect on next session launch (`oc --preset <name>`).

$ARGUMENTS
