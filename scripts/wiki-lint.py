#!/usr/bin/env python3
"""Lint wiki content health for Karpathy-style setup.

Checks:
1) Dead wikilinks
2) Pages missing from index.md
3) Orphan pages (no inbound links and not in index)
4) Missing frontmatter dates (created/updated)
5) Missing source traceability (sources frontmatter, Related, References, or inline refs)
6) Stale project pages vs git last commit date
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


WIKI_ROOT = Path.home() / "wiki"
INDEX_FILE = WIKI_ROOT / "index.md"
WIKI_DIR = WIKI_ROOT / "wiki"


@dataclass
class Finding:
    level: str  # error | warning | info
    category: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def strip_code_blocks(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]+`", "", text)
    return text


def extract_wikilinks(text: str) -> list[str]:
    # [[target]] or [[target|label]] or [[target#heading]]
    raw = re.findall(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", text)
    links = []
    for t in raw:
        base = t.split("#", 1)[0].strip()
        if base:
            links.append(base)
    return links


def get_all_pages() -> list[Path]:
    pages = []
    for p in WIKI_DIR.rglob("*.md"):
        # skip internal templates
        if p.name.startswith("_"):
            continue
        pages.append(p)
    return sorted(pages)


def get_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    fm = text[4:end]
    data: dict[str, str] = {}
    for line in fm.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip().strip('"')
    return data


def git_last_commit_date(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()[:10]
    except Exception:
        pass
    return ""


def lint() -> list[Finding]:
    findings: list[Finding] = []

    if not INDEX_FILE.exists():
        return [Finding("error", "index", f"Missing index file: {INDEX_FILE}")]

    pages = get_all_pages()
    slug_to_path = {p.stem: p for p in pages}

    # Collect links and inbound map
    outbound: dict[str, list[str]] = {}
    inbound_count: dict[str, int] = {slug: 0 for slug in slug_to_path}

    for p in pages:
        slug = p.stem
        txt = strip_code_blocks(read_text(p))
        links = extract_wikilinks(txt)
        outbound[slug] = links
        for target in links:
            if target in inbound_count:
                inbound_count[target] += 1

    # 1) Dead links
    for slug, links in outbound.items():
        src = slug_to_path[slug]
        for target in links:
            if target not in slug_to_path and target not in {"index", "log"}:
                findings.append(
                    Finding(
                        "warning",
                        "dead-link",
                        f"{src.relative_to(WIKI_ROOT)} → [[{target}]]",
                    )
                )

    # 2+3) Index coverage + orphan detection (deduplicated)
    index_links = set(extract_wikilinks(strip_code_blocks(read_text(INDEX_FILE))))
    for slug, p in slug_to_path.items():
        in_index = slug in index_links
        has_inbound = inbound_count.get(slug, 0) > 0
        if not in_index and not has_inbound:
            # True orphan: not discoverable at all
            findings.append(
                Finding(
                    "warning",
                    "orphan",
                    f"Orphan (not in index, no inbound links): {p.relative_to(WIKI_ROOT)}",
                )
            )
        elif not in_index:
            # Reachable via links but missing from index
            findings.append(
                Finding(
                    "info",
                    "index-coverage",
                    f"Not in index.md (but has inbound links): {p.relative_to(WIKI_ROOT)}",
                )
            )

    # 4/5) Frontmatter dates + source traceability
    for p in pages:
        txt = read_text(p)
        fm = get_frontmatter(txt)
        rel = p.relative_to(WIKI_ROOT)
        if not fm.get("created") or not fm.get("updated"):
            findings.append(
                Finding(
                    "warning",
                    "frontmatter",
                    f"Missing created/updated in {rel}",
                )
            )
        # Traceability: sources frontmatter, Related, References, or inline [ref:]
        has_sources_fm = bool(fm.get("sources", "").strip("[] "))
        has_related = "## Related" in txt
        has_references = "## References" in txt
        has_inline_refs = "[ref:" in txt
        if not (has_sources_fm or has_related or has_references or has_inline_refs):
            findings.append(
                Finding(
                    "info",
                    "traceability",
                    f"No source attribution in {rel}",
                )
            )

    # 6) Stale project pages
    projects_dir = WIKI_DIR / "projects"
    if projects_dir.exists():
        for p in projects_dir.glob("*.md"):
            txt = read_text(p)
            fm = get_frontmatter(txt)
            updated = fm.get("updated", "")
            # Look for: - Path: `/abs/path`
            m = re.search(r"^-\s*Path:\s*`([^`]+)`\s*$", txt, flags=re.MULTILINE)
            if not m:
                continue
            path_str = m.group(1)
            proj = Path(path_str).expanduser()
            if not proj.exists():
                findings.append(
                    Finding(
                        "warning",
                        "project-path",
                        f"Project path does not exist: {p.relative_to(WIKI_ROOT)} -> {path_str}",
                    )
                )
                continue
            last_commit = git_last_commit_date(proj)
            if updated and last_commit and last_commit > updated:
                findings.append(
                    Finding(
                        "warning",
                        "stale-project-page",
                        f"{p.relative_to(WIKI_ROOT)} updated={updated}, repo_last_commit={last_commit}",
                    )
                )

    return findings


def main() -> int:
    json_mode = "--json" in sys.argv

    findings = lint()
    counts = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        counts[f.level] = counts.get(f.level, 0) + 1

    if json_mode:
        print(
            json.dumps(
                {"counts": counts, "findings": [f.__dict__ for f in findings]}, indent=2
            )
        )
        return 1 if counts["error"] > 0 else 0

    print("Wiki Lint Report")
    print(
        f"  errors: {counts['error']}  warnings: {counts['warning']}  info: {counts['info']}"
    )
    print()

    if not findings:
        print("  All clean.")
    else:
        for f in findings:
            icon = {
                "error": "\033[31m✗\033[0m",
                "warning": "\033[33m⚠\033[0m",
                "info": "•",
            }.get(f.level, "-")
            print(f"  {icon} [{f.category}] {f.message}")

    return 1 if counts["error"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
