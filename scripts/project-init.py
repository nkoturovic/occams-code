#!/usr/bin/env python3
"""Compatibility wrapper for occams-agentic project initialization.

The source of truth lives at ~/.agents/scripts/project-init.py.
occams-code keeps this wrapper so older `oc --init-project` references and
manual paths continue to work without duplicating universal logic.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    script = Path.home() / ".agents" / "scripts" / "project-init.py"
    if not script.exists():
        print(
            "[ERROR] Missing ~/.agents/scripts/project-init.py. "
            "Install occams-agentic first.",
            file=sys.stderr,
        )
        return 1

    os.execv(sys.executable, [sys.executable, str(script), *sys.argv[1:]])
    return 1  # unreachable unless exec fails


if __name__ == "__main__":
    raise SystemExit(main())
