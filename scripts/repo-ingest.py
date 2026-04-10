#!/usr/bin/env python3
"""Ingest a GitHub repository snapshot into Karpathy-style wiki raw storage.

Creates a digest bundle in ~/wiki/raw/repos/ and a corresponding source-summary
page in ~/wiki/wiki/sources/.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


WIKI_ROOT = Path.home() / "wiki"
RAW_REPOS = WIKI_ROOT / "raw" / "repos"
WIKI_SOURCES = WIKI_ROOT / "wiki" / "sources"
WIKI_INDEX = WIKI_ROOT / "index.md"
WIKI_LOG = WIKI_ROOT / "log.md"


def parse_repo_ref(value: str) -> tuple[str, str]:
    value = value.strip()
    if value.startswith(("http://", "https://")):
        parsed = urlparse(value)
        if parsed.netloc not in {"github.com", "www.github.com"}:
            raise ValueError("Only github.com URLs are supported")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise ValueError("Invalid GitHub repository URL")
        owner, repo = parts[0], parts[1]
    else:
        if "/" not in value:
            raise ValueError("Use owner/repo or GitHub URL")
        owner, repo = value.split("/", 1)

    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Invalid repository reference")
    return owner, repo


def run_cmd(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, obj: object) -> None:
    write_text(path, json.dumps(obj, indent=2, ensure_ascii=False))


def update_index(source_slug: str, repo_name: str) -> None:
    if not WIKI_INDEX.exists():
        write_text(
            WIKI_INDEX,
            "# Wiki Index\n\nMaster routing table. Agent: read this first to find relevant pages.\n\n## Source Summaries\n",
        )

    text = WIKI_INDEX.read_text(encoding="utf-8")
    entry = f"- [[{source_slug}]] — {repo_name} repository digest\n"
    if entry in text:
        return

    section = "## Source Summaries"
    if section not in text:
        text += "\n## Source Summaries\n"

    idx = text.index(section) + len(section)
    remainder = text[idx:]
    next_section = remainder.find("\n## ")
    insert_pos = len(text) if next_section == -1 else idx + next_section

    before = text[:insert_pos]
    after = text[insert_pos:]
    before = before.replace("(none yet — summaries of ingested sources)\n", "")
    if not before.endswith("\n"):
        before += "\n"

    write_text(WIKI_INDEX, before + entry + after)


def append_log(repo_name: str, bundle_rel: str, source_page_rel: str) -> None:
    if not WIKI_LOG.exists():
        write_text(WIKI_LOG, "# Wiki Log\n\n")

    today = dt.date.today().isoformat()
    entry = (
        f"\n## [{today}] ingest | {repo_name} repo digest\n"
        f"Source: {bundle_rel}\n"
        f"Pages created: {source_page_rel}\n"
        f"Notes: Repo metadata/issues/PRs snapshot captured for wiki ingestion.\n"
    )
    with WIKI_LOG.open("a", encoding="utf-8") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# Code-derived insights helpers
# ---------------------------------------------------------------------------

_TEST_PATH_RE = re.compile(
    r"(?:^|/)(?:test|tests|spec|__tests__|testing)(?:/|$)", re.IGNORECASE
)
_TEST_FILE_RE = re.compile(r"(?:test|spec)_.*\.|.*(?:test|spec)\.", re.IGNORECASE)
_CI_WORKFLOW_RE = re.compile(r"^\.github/workflows/.*\.(yml|yaml)$")
_DOCS_PATH_RE = re.compile(r"(?:^|/)docs/|\.md$", re.IGNORECASE)

_MONOREPO_SIGNALS = [
    "packages/",
    "apps/",
    "pnpm-workspace.yaml",
    "turbo.json",
    "lerna.json",
    "nx.json",
    "bazel-workspace",
    "WORKSPACE",
    "BUCK",
]
_SERVICE_SIGNALS = [
    "cmd/",
    "internal/",
    "api/",
    "server/",
    "service/",
    "services/",
    "deploy/",
    "infra/",
]
_FRONTEND_SIGNALS = [
    "src/components",
    "src/views",
    "pages/",
    "app/",
    "public/",
    "static/",
    "assets/",
    "nuxt.config",
    "next.config",
    "vite.config",
]
_LIBRARY_SIGNALS = [
    "lib/",
    "include/",
    "src/lib",
    "pkg/",
    "dist/",
]


def _tree_paths(tree_obj: dict) -> list[str]:
    """Extract file paths from a GitHub tree API response."""
    return [
        e.get("path", "")
        for e in tree_obj.get("tree", [])
        if e.get("type") == "blob" and e.get("path")
    ]


def analyze_tree_paths(paths: list[str]) -> dict:
    """Return tree-derived metrics from a list of file paths."""
    total = len(paths)
    ext_counter: Counter[str] = Counter()
    top_folder_counter: Counter[str] = Counter()
    test_count = 0
    ci_count = 0
    docs_count = 0

    for p in paths:
        # Extension histogram
        dot = p.rfind(".")
        if dot >= 0 and "/" not in p[dot:]:
            ext_counter[p[dot:].lower()] += 1
        else:
            ext_counter["(no ext)"] += 1

        # Top-level folder
        parts = p.split("/", 1)
        if len(parts) > 1:
            top_folder_counter[parts[0]] += 1

        # Test heuristic
        if _TEST_PATH_RE.search(p) or _TEST_FILE_RE.search(p):
            test_count += 1

        # CI workflows
        if _CI_WORKFLOW_RE.match(p):
            ci_count += 1

        # Docs
        if _DOCS_PATH_RE.search(p):
            docs_count += 1

    top_exts = ext_counter.most_common(15)
    top_folders = top_folder_counter.most_common(15)

    return {
        "total_files": total,
        "extension_histogram": [
            {"extension": ext, "count": cnt} for ext, cnt in top_exts
        ],
        "top_level_folder_histogram": [
            {"folder": f, "count": c} for f, c in top_folders
        ],
        "test_file_count": test_count,
        "ci_workflow_count": ci_count,
        "docs_count": docs_count,
    }


def detect_architecture_signals(paths: list[str]) -> list[str]:
    """Detect architecture signals from file paths."""
    path_set = set(paths)
    signals: list[str] = []

    # Monorepo
    mono_hits = [
        s for s in _MONOREPO_SIGNALS if any(p.startswith(s) or s in p for p in path_set)
    ]
    if mono_hits:
        signals.append(f"monorepo ({', '.join(sorted(set(mono_hits)))})")

    # Service / backend
    svc_hits = [s for s in _SERVICE_SIGNALS if any(p.startswith(s) for p in path_set)]
    if svc_hits:
        signals.append(f"service/backend ({', '.join(sorted(set(svc_hits)))})")

    # Frontend
    fe_hits = [
        s for s in _FRONTEND_SIGNALS if any(p.startswith(s) or s in p for p in path_set)
    ]
    if fe_hits:
        signals.append(f"frontend ({', '.join(sorted(set(fe_hits)))})")

    # Library
    lib_hits = [s for s in _LIBRARY_SIGNALS if any(p.startswith(s) for p in path_set)]
    if lib_hits:
        signals.append(f"library ({', '.join(sorted(set(lib_hits)))})")

    return signals


# Key file candidates in priority order
_KEY_FILE_CANDIDATES = [
    "package.json",
    "pnpm-workspace.yaml",
    "turbo.json",
    "pyproject.toml",
    "requirements.txt",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
]

_MAX_KEY_FILES = 12
_MAX_FILE_BYTES = 200_000


def fetch_key_files(
    repo_full: str, paths: list[str], bundle_dir: Path, warnings: list[str]
) -> dict[str, str]:
    """Fetch key config files via gh api (raw). Returns {relative_path: content}."""
    artifacts_dir = bundle_dir / "code_artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    fetched: dict[str, str] = {}
    path_set = set(paths)

    # Collect candidates present in tree
    candidates: list[str] = []
    for c in _KEY_FILE_CANDIDATES:
        if c in path_set:
            candidates.append(c)

    # Add CI workflow files
    for p in sorted(path_set):
        if _CI_WORKFLOW_RE.match(p) and p not in candidates:
            candidates.append(p)

    # Limit
    candidates = candidates[:_MAX_KEY_FILES]

    for rel_path in candidates:
        safe_name = rel_path.replace("/", "__")
        result = run_cmd(
            [
                "gh",
                "api",
                f"repos/{repo_full}/contents/{rel_path}",
                "-H",
                "Accept: application/vnd.github.raw",
            ],
            timeout=30,
        )
        if result.returncode != 0:
            warnings.append(f"Could not fetch key file: {rel_path}")
            continue
        content = result.stdout
        if len(content.encode("utf-8", errors="replace")) > _MAX_FILE_BYTES:
            content = content[:_MAX_FILE_BYTES]
            warnings.append(f"Truncated key file: {rel_path}")
        dest = artifacts_dir / safe_name
        write_text(dest, content)
        fetched[rel_path] = content

    return fetched


def _parse_package_json_deps(content: str) -> list[str]:
    """Extract notable dependency hints from package.json."""
    hints: list[str] = []
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return hints

    all_deps = {}
    for section in ("dependencies", "devDependencies"):
        all_deps.update(obj.get(section, {}))

    # Framework / tool heuristics
    _JS_HINTS = {
        "react": "React",
        "react-dom": "React",
        "next": "Next.js",
        "nuxt": "Nuxt",
        "vue": "Vue",
        "angular": "Angular",
        "@angular/core": "Angular",
        "svelte": "Svelte",
        "@sveltejs/kit": "SvelteKit",
        "express": "Express",
        "fastify": "Fastify",
        "koa": "Koa",
        "nestjs": "NestJS",
        "@nestjs/core": "NestJS",
        "typescript": "TypeScript",
        "ts-node": "TypeScript",
        "eslint": "ESLint",
        "prettier": "Prettier",
        "jest": "Jest",
        "vitest": "Vitest",
        "mocha": "Mocha",
        "webpack": "Webpack",
        "vite": "Vite",
        "rollup": "Rollup",
        "tailwindcss": "Tailwind CSS",
        "@tanstack/react-query": "TanStack Query",
        "prisma": "Prisma",
        "drizzle-orm": "Drizzle ORM",
        "zod": "Zod",
        "axios": "Axios",
        "lodash": "Lodash",
        "dayjs": "Day.js",
        "moment": "Moment.js",
    }
    for dep_key in all_deps:
        if dep_key in _JS_HINTS:
            hint = _JS_HINTS[dep_key]
            if hint not in hints:
                hints.append(hint)
    return hints


def _parse_python_deps(content: str, filename: str) -> list[str]:
    """Extract dependency hints from pyproject.toml or requirements.txt."""
    hints: list[str] = []
    _PY_HINTS = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "starlette": "Starlette",
        "sanic": "Sanic",
        "pydantic": "Pydantic",
        "sqlalchemy": "SQLAlchemy",
        "alembic": "Alembic",
        "celery": "Celery",
        "pytest": "pytest",
        "numpy": "NumPy",
        "pandas": "Pandas",
        "scikit-learn": "scikit-learn",
        "tensorflow": "TensorFlow",
        "torch": "PyTorch",
        "requests": "Requests",
        "httpx": "HTTPX",
        "click": "Click",
        "typer": "Typer",
        "black": "Black",
        "ruff": "Ruff",
        "mypy": "mypy",
    }

    if filename == "pyproject.toml":
        # Simple line-based scan for dependency names
        for line in content.splitlines():
            line_lower = line.strip().lower()
            for key, label in _PY_HINTS.items():
                if key in line_lower:
                    if label not in hints:
                        hints.append(label)
    else:
        # requirements.txt: one dep per line
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue
            dep_name = re.split(r"[=<>!\[]", line, 1)[0].strip().lower()
            for key, label in _PY_HINTS.items():
                if key in dep_name:
                    if label not in hints:
                        hints.append(label)
    return hints


def _parse_rust_deps(content: str) -> list[str]:
    """Extract dependency hints from Cargo.toml."""
    hints: list[str] = []
    _RUST_HINTS = {
        "tokio": "Tokio",
        "actix": "Actix",
        "axum": "Axum",
        "warp": "Warp",
        "rocket": "Rocket",
        "serde": "Serde",
        "clap": "Clap",
        "reqwest": "Reqwest",
        "diesel": "Diesel",
        "sqlx": "SQLx",
    }
    content_lower = content.lower()
    for key, label in _RUST_HINTS.items():
        if key in content_lower:
            hints.append(label)
    return hints


def _parse_go_deps(content: str) -> list[str]:
    """Extract module hints from go.mod."""
    hints: list[str] = []
    _GO_HINTS = {
        "gin-gonic": "Gin",
        "echo": "Echo",
        "fiber": "Fiber",
        "chi": "Chi",
        "gorm": "GORM",
        "sqlx": "sqlx (Go)",
        "grpc": "gRPC",
    }
    for line in content.splitlines():
        line_lower = line.lower()
        for key, label in _GO_HINTS.items():
            if key in line_lower and label not in hints:
                hints.append(label)
    return hints


def _parse_jvm_deps(content: str) -> list[str]:
    """Extract dependency hints from pom.xml or build.gradle."""
    hints: list[str] = []
    _JVM_HINTS = {
        "spring": "Spring",
        "hibernate": "Hibernate",
        "junit": "JUnit",
        "mockito": "Mockito",
        "kotlin": "Kotlin",
        "gradle": "Gradle",
        "maven": "Maven",
        "micronaut": "Micronaut",
        "quarkus": "Quarkus",
    }
    content_lower = content.lower()
    for key, label in _JVM_HINTS.items():
        if key in content_lower and label not in hints:
            hints.append(label)
    return hints


def parse_stack_hints(fetched: dict[str, str]) -> list[str]:
    """Parse fetched key files for stack hints."""
    hints: list[str] = []
    seen: set[str] = set()

    for rel_path, content in fetched.items():
        basename = rel_path.rsplit("/", 1)[-1] if "/" in rel_path else rel_path

        new: list[str] = []
        if basename == "package.json":
            new = _parse_package_json_deps(content)
        elif basename in ("pyproject.toml", "requirements.txt"):
            new = _parse_python_deps(content, basename)
        elif basename == "Cargo.toml":
            new = _parse_rust_deps(content)
        elif basename == "go.mod":
            new = _parse_go_deps(content)
        elif basename in ("pom.xml", "build.gradle"):
            new = _parse_jvm_deps(content)

        for h in new:
            if h not in seen:
                seen.add(h)
                hints.append(h)

    return hints


def derive_conclusions(
    tree_metrics: dict,
    arch_signals: list[str],
    stack_hints: list[str],
    languages: dict | None,
) -> list[str]:
    """Produce human-readable derived conclusions."""
    conclusions: list[str] = []

    # Primary language(s)
    if languages:
        sorted_langs = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
        if sorted_langs:
            top = sorted_langs[0][0]
            top_pct = round(
                sorted_langs[0][1] / max(sum(v for _, v in sorted_langs), 1) * 100
            )
            conclusions.append(f"Primary language: {top} (~{top_pct}% of codebase)")
            if len(sorted_langs) > 1:
                others = ", ".join(
                    f"{l} (~{round(v / max(sum(vv for _, vv in sorted_langs), 1) * 100)}%)"
                    for l, v in sorted_langs[1:4]
                )
                conclusions.append(f"Other languages: {others}")

    # Architecture
    if arch_signals:
        conclusions.append(f"Architecture signals: {'; '.join(arch_signals)}")
    else:
        conclusions.append(
            "No strong architecture signals detected (likely a simple/single-purpose repo)"
        )

    # Test ratio
    total = tree_metrics.get("total_files", 0)
    test_count = tree_metrics.get("test_file_count", 0)
    if total > 0:
        test_pct = round(test_count / total * 100, 1)
        if test_pct > 10:
            conclusions.append(
                f"Good test coverage signal: {test_count} test files ({test_pct}%)"
            )
        elif test_pct > 0:
            conclusions.append(
                f"Moderate test coverage: {test_count} test files ({test_pct}%)"
            )
        else:
            conclusions.append(
                "No test files detected — coverage may be low or tests live elsewhere"
            )

    # CI
    ci_count = tree_metrics.get("ci_workflow_count", 0)
    if ci_count > 0:
        conclusions.append(f"CI configured: {ci_count} workflow(s)")
    else:
        conclusions.append("No CI workflows detected")

    # Docs
    docs_count = tree_metrics.get("docs_count", 0)
    if docs_count > 5:
        conclusions.append(f"Well-documented: {docs_count} doc files")
    elif docs_count > 0:
        conclusions.append(f"Some documentation present: {docs_count} doc files")
    else:
        conclusions.append("Minimal documentation detected")

    # Stack hints
    if stack_hints:
        conclusions.append(f"Stack hints: {', '.join(stack_hints[:15])}")

    return conclusions


def generate_code_insights(
    repo_full: str,
    tree_obj: dict | None,
    languages: dict | None,
    fetched_files: dict[str, str],
    warnings: list[str],
) -> tuple[dict, str]:
    """Generate code_insights.json data and code_insights.md content."""
    paths = _tree_paths(tree_obj) if tree_obj else []
    tree_metrics = analyze_tree_paths(paths) if paths else {"total_files": 0}
    arch_signals = detect_architecture_signals(paths) if paths else []
    stack_hints = parse_stack_hints(fetched_files)

    conclusions = derive_conclusions(tree_metrics, arch_signals, stack_hints, languages)

    insights_json = {
        "repo": repo_full,
        "generated_at": dt.datetime.now().isoformat(),
        "tree_metrics": tree_metrics,
        "architecture_signals": arch_signals,
        "stack_hints": stack_hints,
        "derived_conclusions": conclusions,
    }

    # Build markdown
    lines: list[str] = []
    lines.append(f"# Code Insights: {repo_full}")
    lines.append("")
    lines.append(f"_Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    lines.append("")

    # Primary language
    if languages:
        sorted_langs = sorted(languages.items(), key=lambda kv: kv[1], reverse=True)
        lines.append("## Primary Language(s)")
        for lang, size in sorted_langs[:5]:
            total_size = sum(v for _, v in sorted_langs)
            pct = round(size / max(total_size, 1) * 100, 1)
            lines.append(f"- **{lang}**: {pct}%")
        lines.append("")

    # Architecture
    lines.append("## Architectural Shape")
    if arch_signals:
        for sig in arch_signals:
            lines.append(f"- {sig}")
    else:
        lines.append("- No strong architecture signals detected")
    lines.append("")

    # Build / Test / CI
    lines.append("## Build / Test / CI Signals")
    total = tree_metrics.get("total_files", 0)
    test_count = tree_metrics.get("test_file_count", 0)
    ci_count = tree_metrics.get("ci_workflow_count", 0)
    docs_count = tree_metrics.get("docs_count", 0)
    lines.append(f"- Total files: {total}")
    lines.append(f"- Test files: {test_count}")
    lines.append(f"- CI workflows: {ci_count}")
    lines.append(f"- Doc files: {docs_count}")
    lines.append("")

    # Stack hints
    if stack_hints:
        lines.append("## Notable Stack Hints")
        for hint in stack_hints[:20]:
            lines.append(f"- {hint}")
        lines.append("")

    # Derived conclusions
    lines.append("## Derived Conclusions")
    for c in conclusions:
        lines.append(f"- {c}")
    lines.append("")

    # Confidence
    lines.append("## Confidence Notes")
    lines.append("- Insights are derived from file paths and key config files only")
    lines.append("- No runtime analysis or dependency resolution is performed")
    lines.append("- Test file detection uses path/filename heuristics")
    lines.append("")

    insights_md = "\n".join(lines)
    return insights_json, insights_md


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest GitHub repo into wiki raw storage"
    )
    parser.add_argument("repo", help="owner/repo or GitHub URL")
    parser.add_argument(
        "--no-repomix",
        action="store_true",
        help="Skip repomix packaging even if repomix is installed",
    )
    args = parser.parse_args()

    if not shutil.which("gh"):
        print("[ERROR] GitHub CLI (gh) is required")
        return 1

    try:
        owner, repo = parse_repo_ref(args.repo)
    except ValueError as e:
        print(f"[ERROR] {e}")
        return 1

    today = dt.date.today().isoformat()
    repo_key = f"{owner}--{repo}".lower()
    bundle_name = f"{today}_{repo_key}"
    bundle_dir = RAW_REPOS / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    created_files: list[str] = []
    repo_full = f"{owner}/{repo}"

    # Repo metadata
    meta = run_cmd(["gh", "api", f"repos/{repo_full}"])
    if meta.returncode != 0:
        print(f"[ERROR] Could not fetch repo metadata: {meta.stderr.strip()}")
        return 1
    try:
        meta_obj = json.loads(meta.stdout)
    except json.JSONDecodeError:
        print("[ERROR] Invalid metadata payload from gh api")
        return 1
    write_json(bundle_dir / "repo.json", meta_obj)
    created_files.append("repo.json")

    # README (raw markdown)
    readme = run_cmd(
        [
            "gh",
            "api",
            f"repos/{repo_full}/readme",
            "-H",
            "Accept: application/vnd.github.raw",
        ]
    )
    if readme.returncode == 0 and readme.stdout.strip():
        write_text(bundle_dir / "README.md", readme.stdout)
        created_files.append("README.md")
    else:
        warnings.append("README not available via API")

    # Languages
    langs = run_cmd(["gh", "api", f"repos/{repo_full}/languages"])
    if langs.returncode == 0:
        try:
            write_json(bundle_dir / "languages.json", json.loads(langs.stdout))
            created_files.append("languages.json")
        except json.JSONDecodeError:
            warnings.append("languages payload was not valid JSON")
    else:
        warnings.append("Could not fetch languages")

    # Recursive tree snapshot
    tree = run_cmd(["gh", "api", f"repos/{repo_full}/git/trees/HEAD?recursive=1"])
    if tree.returncode == 0:
        try:
            tree_obj = json.loads(tree.stdout)
            write_json(bundle_dir / "tree.json", tree_obj)
            created_files.append("tree.json")
        except json.JSONDecodeError:
            warnings.append("tree payload was not valid JSON")
    else:
        warnings.append("Could not fetch recursive tree")

    # Issues and PR snapshots (best effort)
    issues = run_cmd(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_full,
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,state,labels,createdAt,updatedAt,url,author",
        ]
    )
    if issues.returncode == 0:
        try:
            write_json(bundle_dir / "issues.json", json.loads(issues.stdout))
            created_files.append("issues.json")
        except json.JSONDecodeError:
            warnings.append("issues payload was not valid JSON")
    else:
        warnings.append("Could not fetch issues list")

    prs = run_cmd(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo_full,
            "--state",
            "all",
            "--limit",
            "100",
            "--json",
            "number,title,state,createdAt,updatedAt,url,author,mergeStateStatus",
        ]
    )
    if prs.returncode != 0:
        # Fallback for older gh versions/field sets.
        prs = run_cmd(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo_full,
                "--state",
                "all",
                "--limit",
                "100",
                "--json",
                "number,title,state,createdAt,updatedAt,url,author",
            ]
        )

    if prs.returncode == 0:
        try:
            write_json(bundle_dir / "pull_requests.json", json.loads(prs.stdout))
            created_files.append("pull_requests.json")
        except json.JSONDecodeError:
            warnings.append("pull request payload was not valid JSON")
    else:
        warnings.append("Could not fetch pull request list")

    # Optional repomix bundle
    repomix_file = bundle_dir / "repomix.xml"
    if not args.no_repomix and shutil.which("repomix"):
        repomix = run_cmd(
            ["repomix", "--remote", repo_full, "-o", str(repomix_file)],
            timeout=600,
        )
        if repomix.returncode == 0 and repomix_file.exists():
            created_files.append("repomix.xml")
        else:
            warnings.append("repomix failed for this repository")
    elif not args.no_repomix:
        warnings.append("repomix not installed (skip packaging)")

    # ------------------------------------------------------------------
    # Code-derived insights (best effort — never hard-fail the ingest)
    # ------------------------------------------------------------------
    tree_obj_for_insights: dict | None = None
    languages_for_insights: dict | None = None
    fetched_key_files: dict[str, str] = {}

    try:
        # Reuse already-fetched data where available
        if (bundle_dir / "tree.json").exists():
            tree_obj_for_insights = json.loads(
                (bundle_dir / "tree.json").read_text(encoding="utf-8")
            )
        if (bundle_dir / "languages.json").exists():
            languages_for_insights = json.loads(
                (bundle_dir / "languages.json").read_text(encoding="utf-8")
            )

        # Fetch key config files (best effort)
        paths_for_fetch = (
            _tree_paths(tree_obj_for_insights) if tree_obj_for_insights else []
        )
        if paths_for_fetch:
            try:
                fetched_key_files = fetch_key_files(
                    repo_full, paths_for_fetch, bundle_dir, warnings
                )
                if fetched_key_files:
                    created_files.append("code_artifacts/")
            except Exception as exc:
                warnings.append(f"Key-file fetch failed: {exc}")

        # Generate insights
        insights_json, insights_md = generate_code_insights(
            repo_full,
            tree_obj_for_insights,
            languages_for_insights,
            fetched_key_files,
            warnings,
        )
        write_json(bundle_dir / "code_insights.json", insights_json)
        created_files.append("code_insights.json")
        write_text(bundle_dir / "code_insights.md", insights_md)
        created_files.append("code_insights.md")
    except Exception as exc:
        warnings.append(f"Code insights generation failed: {exc}")

    manifest = {
        "repo": repo_full,
        "url": f"https://github.com/{repo_full}",
        "created_at": dt.datetime.now().isoformat(),
        "bundle_dir": str(bundle_dir),
        "files": created_files,
        "warnings": warnings,
    }
    write_json(bundle_dir / "manifest.json", manifest)

    # Create/update source summary page
    source_slug = bundle_name
    source_page = WIKI_SOURCES / f"{source_slug}.md"
    if not source_page.exists():
        body = f"""---
summary: \"Repository digest for {repo_full}\"
type: source-summary
tags: [repo, github, {owner.lower()}, {repo.lower()}]
sources: [raw/repos/{bundle_name}/manifest.json]
related: []
created: {today}
updated: {today}
confidence: medium
source_type: repo
raw_file: raw/repos/{bundle_name}/manifest.json
url: https://github.com/{repo_full}
author: {owner}
date_published: unknown
date_ingested: {today}
---

# {repo_full} — Repository Digest

## Snapshot artifacts
"""
        for filename in created_files:
            body += f"- `raw/repos/{bundle_name}/{filename}`\n"

        # Add code-derived insights section
        try:
            if (bundle_dir / "code_insights.json").exists():
                ci = json.loads(
                    (bundle_dir / "code_insights.json").read_text(encoding="utf-8")
                )
                conclusions = ci.get("derived_conclusions", [])
                if conclusions:
                    body += "\n## Code-derived insights\n"
                    for c in conclusions:
                        body += f"- {c}\n"
        except Exception:
            pass  # best effort

        if warnings:
            body += "\n## Warnings\n"
            for w in warnings:
                body += f"- {w}\n"

        body += f"\n## References\n- [ref: raw/repos/{bundle_name}/manifest.json]\n"
        write_text(source_page, body)

    update_index(source_slug, repo_full)
    append_log(repo_full, f"raw/repos/{bundle_name}", f"wiki/sources/{source_slug}.md")

    print(f"[OK] Ingested repository: {repo_full}")
    print(f"[OK] Bundle: {bundle_dir}")
    print(f"[OK] Source summary: {source_page}")
    if warnings:
        print("[WARN] Completed with warnings:")
        for w in warnings:
            print(f"  - {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
