#!/usr/bin/env python3
"""Initialize wiki + local agent workspace for a new project.

Creates/updates the global project wiki page, root AGENTS.md, and a
project-local .agents/ workspace.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path


WIKI_ROOT = Path.home() / ".agents" / "wiki"
WIKI_INDEX = WIKI_ROOT / "index.md"
WIKI_LOG = WIKI_ROOT / "log.md"
WIKI_PROJECTS = WIKI_ROOT / "projects"


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
    the global AGENTS.md rules + ~/.agents/wiki/index.md routing table.
    """
    return f"""# {project_name}

- Global project wiki: `~/.agents/wiki/projects/{slug}.md`
- Global wiki index: `~/.agents/wiki/index.md`
- Project workspace: `.agents/`
  - `.agents/wiki/` — project-local durable notes
  - `.agents/wiki/AGENTS.md` — project-local wiki schema
  - `.agents/wiki/raw/` — project-local immutable sources
  - `.agents/repos/` — cloned/referenced repos (symlinked from `.agents/wiki/raw/repos/`)
  - `.agents/scratch/` — ephemeral files
  - `.agents/skills/` — project-specific skills
- Global rules: `~/.config/opencode/AGENTS.md`

OpenCode auto-loads this file when working in the project. It also auto-loads
global rules from `~/.config/opencode/AGENTS.md` and the system schema from
`~/.agents/AGENTS.md`.

Before starting, read the global project wiki page. If `.agents/wiki/index.md`
exists, read it for project-local notes. When maintaining project-local notes,
follow `.agents/wiki/AGENTS.md`. When you discover stable cross-session facts,
update the global project wiki page and `~/.agents/wiki/log.md`.
"""


def project_wiki_agents_md(project_name: str) -> str:
    return f"""# {project_name} Local Wiki Schema

This project-local wiki follows the same three-layer pattern as the global
`~/.agents/` workspace:

1. `.agents/wiki/raw/` — immutable source material. Read, don't edit.
2. `.agents/wiki/` — durable project-local notes. Agents maintain this.
3. `AGENTS.md` at project root — tool-discovered project instructions.

## Directory Layout

```
.agents/
├── wiki/
│   ├── AGENTS.md
│   ├── index.md
│   ├── log.md
│   ├── overview.md
│   └── raw/
│       └── repos/ -> ../../repos/
├── repos/
├── scratch/
└── skills/
```

The exact folder layout may evolve. Keep the boundary clear: raw sources are
immutable, wiki notes are durable, scratch is ephemeral.
"""


def project_raw_readme(project_name: str) -> str:
    return f"""# {project_name} Raw Sources

Immutable source material for this project's local wiki.

- Put docs/articles/papers under the matching subdirectory.
- Put large cloned repos under `.agents/repos/` (available through
  `.agents/wiki/raw/repos/`).
- Do not edit raw sources; write synthesized notes in `.agents/wiki/`.
"""


def ensure_project_agents_md(slug: str, project_name: str, project_path: Path) -> bool:
    """Create a project-local AGENTS.md if it doesn't exist."""
    agents_file = project_path / "AGENTS.md"
    if agents_file.exists():
        return False
    agents_file.write_text(project_agents_md(slug, project_name), encoding="utf-8")
    return True


def ensure_project_workspace(slug: str, project_name: str, project_path: Path) -> bool:
    """Create a project-local .agents/ workspace if missing.

    AGENTS.md remains at project root for tool discovery. The .agents/ tree
    mirrors ~/.agents/: durable local wiki, repos outside the vault but
    symlinked from wiki/raw/repos, scratch, and optional project skills.
    """
    root = project_path / ".agents"
    created = not root.exists()
    wiki = root / "wiki"
    raw = wiki / "raw"
    repos = root / "repos"

    for directory in (
        wiki / "comparisons",
        wiki / "concepts",
        wiki / "domain",
        wiki / "entities",
        wiki / "languages",
        wiki / "patterns",
        wiki / "sources",
        raw / "articles",
        raw / "papers",
        raw / "docs",
        raw / "forums",
        raw / "assets",
        raw / "user",
        raw / "session-reports",
        raw / "_inbox",
        repos,
        root / "scratch",
        root / "skills",
    ):
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.write_text("", encoding="utf-8")

    raw_repos = raw / "repos"
    if not raw_repos.exists():
        raw_repos.symlink_to("../../repos", target_is_directory=True)

    ensure_file(wiki / "AGENTS.md", project_wiki_agents_md(project_name))
    ensure_file(
        wiki / "index.md",
        f"# {project_name} Local Wiki\n\n"
        f"Project-local notes for `{project_name}`.\n\n"
        f"Global project page: `~/.agents/wiki/projects/{slug}.md`\n\n"
        "## Notes\n",
    )
    ensure_file(wiki / "log.md", f"# {project_name} Local Log\n\n")
    ensure_file(wiki / "overview.md", f"# {project_name} Overview\n\n")
    ensure_file(raw / "README.md", project_raw_readme(project_name))
    return created


def ensure_gitignore_entry(project_path: Path) -> bool:
    """Ignore the project-local .agents/ workspace in git projects."""
    if not (project_path / ".git").exists():
        return False

    gitignore = project_path / ".gitignore"
    text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines = {line.strip() for line in text.splitlines()}
    if ".agents/" in lines or ".agents" in lines:
        return False
    prefix = "" if not text or text.endswith("\n") else "\n"
    with gitignore.open("a", encoding="utf-8") as f:
        f.write(f"{prefix}\n# AI agent workspace\n.agents/\n")
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
        f"Page: projects/{slug}.md\n"
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
    workspace_created = ensure_project_workspace(slug, project_name, project_path)
    gitignore_updated = ensure_gitignore_entry(project_path)
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
    if workspace_created:
        print(f"[OK] Created project workspace at {project_path / '.agents'}")
    if gitignore_updated:
        print("[OK] Added .agents/ to .gitignore")
    if index_updated:
        print("[OK] Added entry to wiki index")

    print("[OK] Project initialization complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
