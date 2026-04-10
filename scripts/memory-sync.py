#!/usr/bin/env python3
"""memory-sync.py - Index projects and wiki for persistent semantic memory.

Uses the local semantic-search backend to index codebases into persistent
project/global memory.

Usage:
  python3 memory-sync.py                       # Index current directory (incremental)
  python3 memory-sync.py --project /path/to/x  # Index a specific project
  python3 memory-sync.py --wiki                # Also index ~/wiki as global memory
  python3 memory-sync.py --wiki-only           # Index only ~/wiki
  python3 memory-sync.py --full                # Force full reindex (not incremental)
  python3 memory-sync.py --list                # List indexed projects and exit
"""

import argparse
import json
import logging
import multiprocessing as mp
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path
from functools import lru_cache

SEMANTIC_ENGINE_DIR = os.path.expanduser("~/.local/share/opencode-context-local")
DEFAULT_STORAGE = str(Path.home() / ".opencode_memory")

# Use OpenCode-neutral storage path by default.
os.environ.setdefault("CODE_SEARCH_STORAGE", DEFAULT_STORAGE)
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("PYTHONWARNINGS", "ignore:resource_tracker:UserWarning")

# Suppress benign shutdown warnings from loky/multiprocessing cleanup.
warnings.filterwarnings(
    "ignore",
    message=r"resource_tracker: There appear to be .* leaked semaphore objects",
)


def _ensure_runtime_dependencies() -> None:
    """Re-exec under semantic engine uv env if deps missing.

    This lets users run `python3 memory-sync.py ...` without caring about the
    backend virtualenv details.
    """
    if os.environ.get("MEMORY_SYNC_UV") == "1":
        return

    try:
        import tree_sitter  # noqa: F401

        return
    except Exception:
        pass

    cmd = [
        "uv",
        "run",
        "--directory",
        SEMANTIC_ENGINE_DIR,
        "python",
        __file__,
        *sys.argv[1:],
    ]
    env = dict(os.environ)
    env["MEMORY_SYNC_UV"] = "1"

    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


_ensure_runtime_dependencies()

# Keep default output concise unless explicitly requested.
logging.basicConfig(level=logging.WARNING)
for _name in (
    "httpx",
    "sentence_transformers",
    "embeddings.sentence_transformer",
    "search.indexer",
    "search.incremental_indexer",
    "mcp_server.code_search_server",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

# Add semantic engine backend to import path
sys.path.insert(0, SEMANTIC_ENGINE_DIR)

from mcp_server.code_search_server import CodeSearchServer


def _index_worker(path: str, incremental: bool, out_queue: mp.Queue):
    """Run a single index operation in a child process.

    Isolates potential hangs in model loading/indexing so the parent can timeout
    and continue safely.
    """
    try:
        server = CodeSearchServer()

        # Skip redundant preload path for CLI speed/reliability.
        try:
            server._maybe_start_model_preload = lambda: None
        except Exception:
            pass

        raw = server.index_directory(path, incremental=incremental)
        out_queue.put({"ok": True, "raw": raw})
    except Exception as e:
        out_queue.put({"ok": False, "error": str(e)})


def parse_index_result(raw_json: str) -> dict:
    """Parse JSON from server.index_directory() and return structured result."""
    data = json.loads(raw_json)
    if "error" in data:
        return {"ok": False, "error": data["error"]}
    return {
        "ok": True,
        "directory": data.get("directory", "?"),
        "files_added": data.get("files_added", 0),
        "files_modified": data.get("files_modified", 0),
        "files_removed": data.get("files_removed", 0),
        "chunks_added": data.get("chunks_added", 0),
        "chunks_removed": data.get("chunks_removed", 0),
        "time_taken": data.get("time_taken", 0),
    }


def print_index_result(result: dict, label: str = ""):
    """Print a human-readable summary of an index operation."""
    prefix = f"[{label}] " if label else ""
    if not result["ok"]:
        print(f"{prefix}FAILED: {result['error']}")
        return
    print(f"{prefix}{result['directory']}")
    print(
        f"  files: +{result['files_added']} ~{result['files_modified']} -{result['files_removed']}"
    )
    print(f"  chunks: +{result['chunks_added']} -{result['chunks_removed']}")
    print(f"  time: {result['time_taken']}s")


def cmd_index(
    path: str, incremental: bool, timeout_seconds: int, verbose: bool
) -> dict:
    """Run an index operation and return parsed result."""
    timeout_seconds = max(1, int(timeout_seconds))
    out_queue: mp.Queue = mp.Queue()
    proc = mp.Process(
        target=_index_worker,
        args=(path, incremental, out_queue),
        daemon=True,
    )
    proc.start()

    start = time.time()
    last_tick = -1
    while proc.is_alive():
        proc.join(1)
        elapsed = int(time.time() - start)
        if verbose and elapsed // 5 != last_tick:
            last_tick = elapsed // 5
            print(f"  [verbose] indexing in progress... {elapsed}s elapsed", flush=True)
        if elapsed >= timeout_seconds:
            break

    if proc.is_alive():
        proc.terminate()
        proc.join(2)
        return {
            "ok": False,
            "error": f"timeout after {timeout_seconds}s",
        }

    if out_queue.empty():
        return {"ok": False, "error": "index worker returned no result"}

    msg = out_queue.get()
    if not msg.get("ok"):
        return {"ok": False, "error": msg.get("error", "index worker failed")}

    return parse_index_result(msg["raw"])


def _git_project_is_clean(project_path: str) -> bool:
    """Best-effort check whether git project has no pending changes."""
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        return False
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            return False
        return result.stdout.strip() == ""
    except Exception:
        return False


def _git_changed_paths(project_path: str) -> list[str]:
    """Return changed paths from git status porcelain (best effort)."""
    git_dir = Path(project_path) / ".git"
    if not git_dir.exists():
        return []
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=8,
        )
        if result.returncode != 0:
            return []

        changed = []
        root = Path(project_path)
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            # porcelain format: XY <path> or rename with old -> new
            raw = line[3:] if len(line) > 3 else line
            if " -> " in raw:
                raw = raw.split(" -> ", 1)[1]
            rel = raw.strip()

            # Expand untracked/changed directories to file paths so extension
            # checks can detect relevant code changes.
            abs_path = root / rel
            if abs_path.is_dir():
                for fp in abs_path.rglob("*"):
                    if fp.is_file():
                        try:
                            changed.append(str(fp.relative_to(root)))
                        except Exception:
                            changed.append(str(fp))
            else:
                changed.append(rel)
        return changed
    except Exception:
        return []


@lru_cache(maxsize=1)
def _supported_extensions() -> set[str]:
    """Load supported extensions from backend chunker with safe fallback."""
    try:
        from chunking.multi_language_chunker import MultiLanguageChunker

        return set(getattr(MultiLanguageChunker, "SUPPORTED_EXTENSIONS", set()))
    except Exception:
        # Conservative fallback to common source/docs extensions
        return {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".md",
            ".sh",
            ".bash",
            ".json",
            ".yaml",
            ".yml",
        }


def _has_supported_git_changes(project_path: str) -> bool:
    """True when git changes include at least one code-like indexable extension."""
    changed = _git_changed_paths(project_path)
    if not changed:
        return False
    exts = _supported_extensions()

    # Project indexing should prioritize code files. Documentation is covered by wiki indexing.
    doc_like_exts = {".md", ".txt", ".rst"}
    exts = {e for e in exts if e not in doc_like_exts}

    for rel in changed:
        if Path(rel).suffix.lower() in exts:
            return True
    return False


def cmd_list(server: CodeSearchServer):
    """List all indexed projects."""
    raw = server.list_projects()
    data = json.loads(raw)

    if "error" in data:
        print(f"Error: {data['error']}")
        return

    projects = data.get("projects", [])
    if not projects:
        print("No projects indexed yet.")
        return

    for proj in projects:
        path = proj.get("project_path", "?")
        name = proj.get("project_name", "?")
        chunks = "?"
        idx_stats = proj.get("index_stats")
        if isinstance(idx_stats, dict):
            chunks = idx_stats.get("total_chunks", "?")
        print(f"  {name:30s}  {path}  ({chunks} chunks)")


def main():
    parser = argparse.ArgumentParser(
        description="Index projects and wiki for persistent semantic memory"
    )
    parser.add_argument(
        "--project",
        "-p",
        metavar="PATH",
        help="Index specified project path instead of cwd",
    )
    parser.add_argument(
        "--wiki",
        "-w",
        action="store_true",
        help="Also index ~/wiki as global memory project",
    )
    parser.add_argument(
        "--wiki-only",
        action="store_true",
        help="Index only ~/wiki (skip project indexing)",
    )
    parser.add_argument(
        "--full",
        "-f",
        action="store_true",
        help="Force full reindex (non-incremental)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List indexed projects and exit",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed indexing logs",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Max seconds per index operation before fail-fast (default: 90)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
        for _name in (
            "mcp_server.code_search_server",
            "search.indexer",
            "search.incremental_indexer",
            "embeddings.sentence_transformer",
            "sentence_transformers",
            "httpx",
        ):
            logging.getLogger(_name).setLevel(logging.INFO)

    # --list: show projects and exit
    if args.list:
        server = CodeSearchServer()
        cmd_list(server)
        return 0

    incremental = not args.full
    project_path = os.path.abspath(args.project) if args.project else os.getcwd()
    wiki_path = os.path.expanduser("~/wiki")
    had_error = False
    do_project = not args.wiki_only
    do_wiki = args.wiki or args.wiki_only

    # Index project (default behavior unless --wiki-only)
    if do_project:
        # Fast path: for clean git repos with incremental mode, skip expensive work.
        if incremental and _git_project_is_clean(project_path):
            print(f"Indexing project: {project_path}")
            print("[project] skipped (git working tree clean)")
        elif incremental and not _has_supported_git_changes(project_path):
            print(f"Indexing project: {project_path}")
            print("[project] skipped (no supported-file git changes)")
        else:
            print(f"Indexing project: {project_path}")
            if args.verbose:
                print(
                    f"  [verbose] Starting project index worker (timeout={args.timeout}s)"
                )
            result = cmd_index(project_path, incremental, args.timeout, args.verbose)
            print_index_result(result, label="project")
            if not result["ok"]:
                had_error = True

    # Optionally index wiki
    if do_wiki:
        if os.path.isdir(wiki_path):
            if do_project:
                print(f"\nIndexing wiki: {wiki_path}")
            else:
                print(f"Indexing wiki: {wiki_path}")
            if args.verbose:
                print(
                    f"  [verbose] Starting wiki index worker (timeout={args.timeout}s)"
                )
            wresult = cmd_index(wiki_path, incremental, args.timeout, args.verbose)
            print_index_result(wresult, label="wiki")
            if not wresult["ok"]:
                had_error = True
        else:
            prefix = "\n" if do_project else ""
            print(f"{prefix}Wiki directory not found: {wiki_path} (skipping)")

    return 1 if had_error else 0


if __name__ == "__main__":
    exit_code = main()
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(exit_code)
