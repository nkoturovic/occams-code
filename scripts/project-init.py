#!/usr/bin/env python3
"""Initialize wiki for a new project.

Creates/updates a project wiki page.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path


WIKI_ROOT = Path.home() / "wiki"
WIKI_INDEX = WIKI_ROOT / "index.md"
WIKI_LOG = WIKI_ROOT / "log.md"
WIKI_PROJECTS = WIKI_ROOT / "wiki" / "projects"


def slugify(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def ensure_wiki_dirs() -> None:
    WIKI_ROOT.mkdir(parents=True, exist_ok=True)
    WIKI_PROJECTS.mkdir(parents=True, exist_ok=True)


def ensure_file(path: Path, default: str = "") -> None:
    if not path.exists():
        path.write_text(default, encoding="utf-8")


def project_page_content(slug: str, project_name: str, project_path: Path) -> str:
    today = dt.date.today().isoformat()
    return f"""---
summary: "Working memory for {project_name}"
type: project
tags: [{slug}, project-memory]
sources: []
related:
  - karpathy-llm-wiki
created: {today}
updated: {today}
confidence: medium
---

# {project_name}

- Path: `{project_path}`
- Purpose: [fill in]

## Current Context
- [ ] Goals
- [ ] Constraints
- [ ] Active decisions

## Session Notes
- {today}: Project initialized via `project-init.py`

## References
- [ref: session {today}]

## Related
- [[karpathy-llm-wiki]]
"""


def project_agents_md(slug: str, project_name: str) -> str:
    """Generate a lightweight project-local AGENTS.md.

    Keeps project-specific context only. Wiki navigation is handled by
    the global AGENTS.md rules + ~/wiki/index.md routing table.
    """
    return f"""# {project_name}

- Project wiki: `~/wiki/wiki/projects/{slug}.md`
- Wiki index (routing table): `~/wiki/index.md`
- Global rules: `~/.config/opencode/AGENTS.md`

When you discover stable facts, update the project wiki page and `~/wiki/log.md`.
"""


def ensure_project_agents_md(slug: str, project_name: str, project_path: Path) -> bool:
    """Create a project-local AGENTS.md if it doesn't exist."""
    agents_file = project_path / "AGENTS.md"
    if agents_file.exists():
        return False
    agents_file.write_text(project_agents_md(slug, project_name), encoding="utf-8")
    return True


def ensure_project_page(
    slug: str, project_name: str, project_path: Path
) -> tuple[Path, bool]:
    page = WIKI_PROJECTS / f"{slug}.md"
    if page.exists():
        return page, False
    page.write_text(
        project_page_content(slug, project_name, project_path), encoding="utf-8"
    )
    return page, True


def update_index(slug: str, project_name: str) -> bool:
    ensure_file(
        WIKI_INDEX,
        "# Wiki Index\n\nMaster routing table. Agent: read this first to find relevant pages.\n\n## Projects\n",
    )

    text = WIKI_INDEX.read_text(encoding="utf-8")
    entry = f"- [[{slug}]] — {project_name}\n"
    if entry in text:
        return False

    projects_header = "## Projects"
    if projects_header not in text:
        text += "\n## Projects\n"

    idx = text.index(projects_header) + len(projects_header)
    remainder = text[idx:]
    next_section = remainder.find("\n## ")

    if next_section == -1:
        insert_pos = len(text)
    else:
        insert_pos = idx + next_section

    before = text[:insert_pos]
    after = text[insert_pos:]

    before = before.replace(
        "(none yet — register your first project when you start coding)\n", ""
    )
    if not before.endswith("\n"):
        before += "\n"

    updated = before + entry + after
    WIKI_INDEX.write_text(updated, encoding="utf-8")
    return True


def append_log(project_name: str, project_path: Path, slug: str) -> None:
    ensure_file(WIKI_LOG, "# Wiki Log\n\n")
    today = dt.date.today().isoformat()
    entry = (
        f"\n## [{today}] init-project | {project_name}\n"
        f"Path: {project_path}\n"
        f"Page: wiki/projects/{slug}.md\n"
        f"Notes: Initialized project wiki memory scaffold and index entry.\n"
    )
    with WIKI_LOG.open("a", encoding="utf-8") as f:
        f.write(entry)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize wiki for current project")
    parser.add_argument(
        "--project-path", default=str(Path.cwd()), help="Project path (default: cwd)"
    )
    parser.add_argument("--name", default=None, help="Override project display name")
    args = parser.parse_args()

    project_path = Path(args.project_path).resolve()
    if not project_path.exists() or not project_path.is_dir():
        print(f"[ERROR] Invalid project path: {project_path}")
        return 1

    project_name = args.name or project_path.name
    slug = slugify(project_name)

    ensure_wiki_dirs()
    page, created = ensure_project_page(slug, project_name, project_path)
    agents_created = ensure_project_agents_md(slug, project_name, project_path)
    index_updated = update_index(slug, project_name)
    if created:
        append_log(project_name, project_path, slug)

    print(f"[OK] Project wiki: {page}")
    if created:
        print("[OK] Created new project page")
    else:
        print("[OK] Project page already exists")
    if agents_created:
        print(f"[OK] Created project AGENTS.md at {project_path / 'AGENTS.md'}")
    if index_updated:
        print("[OK] Added entry to wiki index")

    print("[OK] Project initialization complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
