#!/usr/bin/env python3
"""Detect project memory state for the oc launcher.

Outputs shell-safe variable assignments to stdout:
  HAS_INDEX=0|1
  HAS_WIKI_PAGE=0|1
  IS_EMPTY_DIR=0|1
  INDEX_AGE_DAYS=<int>
  PROJECT_WIKI_PAGE='<path>'
  WIKI_STALE=0|1
  WIKI_UPDATED_DATE='YYYY-MM-DD'
  PROJECT_LAST_COMMIT='YYYY-MM-DD'
  DEAD_WIKI_PAGES='<path1>|<path2>'
"""

import json
import re
import shlex
import subprocess
import time
from pathlib import Path


def _is_same_or_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


def _match_rank(current: Path, candidate: Path):
    if _is_same_or_within(current, candidate):
        return (0, -len(candidate.parts))
    if _is_same_or_within(candidate, current):
        return (1, len(candidate.parts))
    return None


def _git_last_commit_date(path: Path) -> str:
    """Return YYYY-MM-DD of last commit, or '' on failure."""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(path),
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()[:10]
    except Exception:
        pass
    return ""


def _frontmatter_date(text: str, field: str) -> str:
    """Extract a date field from YAML frontmatter."""
    m = re.search(rf"^{field}:\s*(\d{{4}}-\d{{2}}-\d{{2}})", text, re.MULTILINE)
    return m.group(1) if m else ""


def main():
    cwd = Path.cwd().resolve()

    # --- Empty directory heuristic ---
    try:
        entries = [p for p in cwd.iterdir() if p.name != ".git"]
        is_empty = len(entries) == 0
    except Exception:
        is_empty = True

    # --- Semantic index detection ---
    has_index = False
    index_age_days = -1
    best_index_rank = None
    memory_root = Path.home() / ".opencode_memory" / "projects"
    if memory_root.exists():
        for info_file in memory_root.glob("*/project_info.json"):
            try:
                data = json.loads(info_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            project_path = data.get("project_path")
            if not project_path:
                continue
            try:
                candidate = Path(project_path).expanduser().resolve()
            except Exception:
                continue
            rank = _match_rank(cwd, candidate)
            if rank is None:
                continue
            idx_file = info_file.parent / "index" / "code.index"
            if not idx_file.exists():
                continue
            stats = info_file.parent / "index" / "stats.json"
            target = stats if stats.exists() else idx_file
            age_seconds = max(0.0, time.time() - target.stat().st_mtime)
            age_days = int(age_seconds // 86400)
            if best_index_rank is None or rank < best_index_rank:
                best_index_rank = rank
                has_index = True
                index_age_days = age_days

    # --- Wiki page detection ---
    has_wiki_page = False
    project_wiki_page = ""
    best_wiki_rank = None
    wiki_projects = Path.home() / "wiki" / "wiki" / "projects"
    if wiki_projects.exists():
        for page in wiki_projects.glob("*.md"):
            try:
                text = page.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            rank = None
            path_matches = re.findall(
                r"^\s*-\s*Path:\s*`([^`]+)`\s*$", text, flags=re.MULTILINE
            )
            for raw_path in path_matches:
                try:
                    candidate = Path(raw_path).expanduser().resolve()
                except Exception:
                    continue
                current_rank = _match_rank(cwd, candidate)
                if current_rank is None:
                    continue
                if rank is None or current_rank < rank:
                    rank = current_rank
            # Backward-compatible: exact marker in text
            marker = f"`{cwd}`"
            if rank is None and marker in text:
                rank = (0, -len(cwd.parts))
            if rank is None:
                continue
            if best_wiki_rank is None or rank < best_wiki_rank:
                best_wiki_rank = rank
                has_wiki_page = True
                project_wiki_page = str(page)

    # --- Wiki staleness detection ---
    wiki_stale = False
    wiki_updated_date = ""
    project_last_commit = ""
    if project_wiki_page:
        try:
            text = Path(project_wiki_page).read_text(encoding="utf-8", errors="ignore")
            wiki_updated_date = _frontmatter_date(text, "updated")
        except Exception:
            pass
        project_last_commit = _git_last_commit_date(cwd)
        if wiki_updated_date and project_last_commit:
            wiki_stale = project_last_commit > wiki_updated_date

    # --- Dead wiki pages detection ---
    dead_pages = []
    if wiki_projects.exists():
        for page in wiki_projects.glob("*.md"):
            try:
                text = page.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            path_matches = re.findall(
                r"^\s*-\s*Path:\s*`([^`]+)`\s*$", text, flags=re.MULTILINE
            )
            for raw_path in path_matches:
                try:
                    p = Path(raw_path).expanduser().resolve()
                    if not p.exists():
                        dead_pages.append(str(page))
                        break
                except Exception:
                    pass

    # --- Output ---
    print(f"HAS_INDEX={1 if has_index else 0}")
    print(f"HAS_WIKI_PAGE={1 if has_wiki_page else 0}")
    print(f"IS_EMPTY_DIR={1 if is_empty else 0}")
    print(f"INDEX_AGE_DAYS={index_age_days}")
    print(f"PROJECT_WIKI_PAGE={shlex.quote(project_wiki_page)}")
    print(f"WIKI_STALE={1 if wiki_stale else 0}")
    print(f"WIKI_UPDATED_DATE={shlex.quote(wiki_updated_date)}")
    print(f"PROJECT_LAST_COMMIT={shlex.quote(project_last_commit)}")
    print(f"DEAD_WIKI_PAGES={shlex.quote('|'.join(dead_pages))}")


if __name__ == "__main__":
    main()
