---
description: Show active preset and agent models
---
1. Run this bash command to show the current preset and models:

```bash
python3 -c "
import json
from pathlib import Path
cfg = json.loads((Path.home() / '.config/opencode/oh-my-opencode-slim.json').read_text())
preset = cfg['preset']
agents = cfg['presets'][preset]
print(f'Active preset: {preset}')
print()
for agent, conf in agents.items():
    print(f'  {agent}: {conf[\"model\"]}')
print()
print(f'Available: {\", \".join(cfg[\"presets\"].keys())}')
"
```

2. Then ask the user if they want to switch to a different preset. Note: switching takes effect on next session launch (`oc --preset <name>`).

$ARGUMENTS
