#!/usr/bin/env python3
"""Sync AGENTS.md model table from oh-my-opencode-slim.json.

Regenerates the '## Current Config' section so AGENTS.md never drifts
from the actual config. Safe to run repeatedly (idempotent).
"""

import json
import re
import sys
from pathlib import Path

CONFIG = Path.home() / ".config/opencode/oh-my-opencode-slim.json"
AGENTS_MD = Path.home() / ".config/opencode/AGENTS.md"


def build_table(config: dict) -> str:
    presets = config.get("presets", {})
    preset_names = sorted(presets.keys())
    agents = sorted(
        {a for p in presets.values() for a in p},
        key=lambda a: (
            [
                "orchestrator",
                "oracle",
                "fixer",
                "designer",
                "explorer",
                "librarian",
            ].index(a)
            if a
            in ["orchestrator", "oracle", "fixer", "designer", "explorer", "librarian"]
            else 99
        ),
    )

    header = "| Agent | " + " | ".join(n.capitalize() for n in preset_names) + " |"
    sep = "|-------|" + "|".join("-" * (len(n) + 2) for n in preset_names) + "|"

    rows = []
    for agent in agents:
        cells = []
        for pname in preset_names:
            model = presets.get(pname, {}).get(agent, {}).get("model", "—")
            # Strip provider prefix for readability
            short = model.split("/", 1)[-1] if "/" in model else model
            cells.append(short)
        rows.append(f"| {agent} | " + " | ".join(cells) + " |")

    fallback = config.get("fallback", {})
    timeout_s = fallback.get("timeoutMs", 60000) // 1000

    lines = [
        f"**{len(preset_names)} presets:** "
        + " → ".join(f"`{n}`" for n in preset_names),
        "",
        header,
        sep,
        *rows,
        "",
        f"**Fallback chains:** {len(next(iter(fallback.get('chains', {}).values()), []))} entries each, quality → cost gradient, auto-trigger on {timeout_s}s timeout.",
    ]
    return "\n".join(lines)


def main() -> int:
    if not CONFIG.exists():
        print(f"[ERROR] Config not found: {CONFIG}", file=sys.stderr)
        return 1
    if not AGENTS_MD.exists():
        print(f"[ERROR] AGENTS.md not found: {AGENTS_MD}", file=sys.stderr)
        return 1

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    text = AGENTS_MD.read_text(encoding="utf-8")

    new_table = build_table(config)

    # Replace the section between "## Current Config" and the next "##"
    pattern = r"(## Current Config\n\n)(.*?)(\n## )"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        print(
            "[WARN] Could not find '## Current Config' section in AGENTS.md",
            file=sys.stderr,
        )
        return 1

    updated = text[: match.start(2)] + new_table + "\n" + text[match.start(3) :]

    if updated == text:
        print("[OK] AGENTS.md already in sync.")
        return 0

    AGENTS_MD.write_text(updated, encoding="utf-8")
    print("[OK] AGENTS.md model table synced from config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
