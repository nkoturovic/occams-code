---
description: Show active preset and agent models
---
1. Run this bash command to show the current preset and models (checks project config first, then global):

```bash
python3 <<'PY'
import copy
import json
from pathlib import Path


def strip_jsonc(text):
    out, i, in_str, esc = [], 0, False, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
        elif c == '/' and i + 1 < len(text) and text[i + 1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            out.append('\n')
            continue
        elif c == '/' and i + 1 < len(text) and text[i + 1] == '*':
            i = text.find('*/', i + 2)
            i = len(text) if i == -1 else i + 2
            continue
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def remove_trailing_commas(text):
    out, i, in_str, esc = [], 0, False, False
    while i < len(text):
        c = text[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif c == ',':
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j >= len(text) or text[j] not in '}]':
                out.append(c)
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def load(path):
    return json.loads(remove_trailing_commas(strip_jsonc(path.read_text())))


def deep_merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        merged = copy.deepcopy(base)
        for key, value in override.items():
            merged[key] = deep_merge(merged.get(key), value)
        return merged
    return copy.deepcopy(override)


def model_label(value):
    if isinstance(value, list):
        if not value:
            return '<none>'
        return f'{value[0]} (+{len(value) - 1} fallbacks)' if len(value) > 1 else value[0]
    return value or '<unset>'


global_path = Path.home() / '.config/opencode/oh-my-opencode-slim.jsonc'
if not global_path.exists():
    global_path = Path.home() / '.config/opencode/oh-my-opencode-slim.json'
project_path = Path('.opencode/oh-my-opencode-slim.jsonc')
if not project_path.exists():
    project_path = Path('.opencode/oh-my-opencode-slim.json')

cfg = load(global_path)
pc = load(project_path) if project_path.exists() else {}

preset = pc.get('preset', cfg['preset'])
source = f'project ({project_path})' if 'preset' in pc else 'global'

if preset not in cfg['presets']:
    print(f'Warning: preset {preset!r} not found, using global default')
    preset, source = cfg['preset'], 'global (fallback)'

agents = copy.deepcopy(cfg['presets'][preset])
if preset in pc.get('presets', {}):
    agents = deep_merge(agents, pc['presets'][preset])
    if source == 'global':
        source = f'global + project overrides ({project_path})'
for name, override in pc.get('agents', {}).items():
    agents[name] = deep_merge(agents.get(name, {}), override)
    if source == 'global':
        source = f'global + project overrides ({project_path})'

print(f'Active: {preset} ({source})')
for agent, conf in agents.items():
    print(f'  {agent}: {model_label(conf.get("model"))}')
print(f'Available: {", ".join(cfg["presets"].keys())}')
print('Switch: oc --preset <name>')
PY
```

$ARGUMENTS
