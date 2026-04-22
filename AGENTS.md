# OpenCode — Agent Rules & Setup

## Session Rules
- Wait for the user's first message before doing anything.
- **On session start**, read `~/wiki/index.md` to discover available project pages and knowledge. Apply relevant context silently (don't narrate it unless asked). **Throughout the session**, consult wiki before starting any task — not just at the start.
- If this is an unfamiliar project (no wiki page, not your own repo), check for instruction files the project may have: `CLAUDE.md`, `.github/copilot-instructions.md`, `.copilot/`, `.cursorrules`, `.windsurfrules`, or similar. Read them if found — they contain project conventions. Our `AGENTS.md` takes precedence on conflicts.
- Keep changes traceable and update wiki/log when durable knowledge is produced.
- Respond in English unless the user asks otherwise.
- **Never push, upload, post, or transmit** code, files, or data to any external service, URL, or API without explicit user approval. This includes `git push`, `curl POST`, file uploads, and any network operation that sends data outbound. Local file reads, command execution, and tool usage are fine.

## Workflow Principles

### Occam's Code *(solution design)*
**The simplest solution that fully solves the problem is the correct solution.**
Fewest changes. Fewest files. Fewest abstractions. If two approaches work equally, the shorter wins.

### Plan & Ask Questions
- Present plans to the user for review before executing — good plans make parallel execution safe; good plans produce good TODOs.
- Any uncertainty or ambiguity → stop and ask the user before proceeding.
- Better to ask too many questions upfront than to execute the wrong plan in parallel.
- When presenting options, state your recommendation and why.

### Divide and Conquer
- Break tasks into independent subtasks that can execute in parallel via agents.
- Use TODOs to track decomposition — `todowrite` is visible in OpenCode's UI.
- Prefer parallel agent tasks over sequential mega-tasks — run as many in parallel as independence allows.

### Parallelize
- Delegate to specialists (`@explorer`, `@fixer`, `@librarian`) — they run concurrently.
- Fire multiple searches in parallel before reading files.
- Combine results after parallel work completes.

### Wiki
- **On session start**, read `~/wiki/index.md` — the routing table to all project pages, conventions, patterns.
- Check wiki **before** starting any task. Stale wiki is worse than no wiki — update it continuously.
- When discovering stable facts, proactively persist them:
  - Per-project → `~/wiki/wiki/projects/<slug>.md` (match by `Path:` field)
  - Language/pattern → `~/wiki/wiki/languages/` or `~/wiki/wiki/patterns/`
  - Global → `~/wiki/wiki/concepts/` or `~/wiki/wiki/entities/`
  - **Always** → append to `~/wiki/log.md` with date, project, and what changed
  - **Always** → update `~/wiki/index.md` if you created a new page
- **Retrieval order:** Wiki → Code search → context7 → grep_app → websearch

### Be Terse
- **Be terse.** Drop filler, keep technical accuracy. "Segfault on null ptr. Add guard." beats a paragraph saying the same thing.
- Don't re-read files you already have in context.
- Don't narrate wiki contents — apply silently.
- Keep AGENTS.md concise — models prioritize content at the top.
- One-word answers are fine when appropriate.

## Agent Types & Delegation

| Agent | When to delegate | Key capability |
|-------|-----------------|----------------|
| **@explorer** | Discover files/symbols before reading | Glob, grep, AST — 3x faster search |
| **@fixer** | Bounded implementation, test writing | 2x faster edits |
| **@librarian** | Library docs, API references | 10x better at current APIs |
| **@oracle** | Architecture, code review, complex debugging | Deep reasoning, trade-offs |
| **@designer** | UI/UX, responsive layouts, visual polish | 10x better UI/UX |
| **@council** | Critical decisions needing diverse perspectives | Multi-LLM consensus |

**Don't delegate when:**
- Single small change (<20 lines, one file)
- You already have the file in context
- Explaining the task takes longer than doing it
- The task is sequential — each step depends on the previous step's output
- You're debugging a single issue through a call chain

**Do delegate when:**
- Multiple independent files need simultaneous changes → parallel @fixer
- Codebase exploration before implementation → @explorer
- Library API behavior uncertain → @librarian
- Architecture decision with trade-offs → @oracle or @council

## Non-text Content

`@designer` is the visual specialist — route all non-text files there.

**For the orchestrator (text-only):** Before using `Read`, check the extension. If it matches an image (png, jpg, jpeg, gif, webp, svg, bmp, ico, tiff, avif) or PDF → delegate to `@designer`. Do NOT `Read` these types yourself — you cannot perceive them.

**For @designer:** Use `zai_vision` MCP tools for all image/PDF analysis. The `Read` tool cannot deliver image content to models (known platform limitation). Call MCP tools directly with the file path — the MCP server reads files from disk itself. SVG is XML text — you CAN read it for structure, but delegate to @designer for visual questions.

| Situation | Action |
|-----------|--------|
| Image/PDF on disk | Delegate file path to `@designer` |
| User asks to "analyze" / "describe" / "look at" a visual | Delegate to `@designer` |
| URL to image/PDF | `webfetch` with `save_binary=true` → delegate saved path |
| Inline pasted image/PDF (no file on disk) | Extract via command below → delegate path to @designer |
| Video/audio | If `zai_vision` MCP is configured, use `video_analysis`. Otherwise suggest external tools. |

Extraction fails → ask user to save to disk.

**Inline paste extraction** (run this, then delegate the output path to @designer):
```bash
MIME=$(sqlite3 ~/.local/share/opencode/opencode.db "SELECT json_extract(data,'$.mime') FROM part WHERE json_extract(data,'$.mime') LIKE 'image%' OR json_extract(data,'$.mime')='application/pdf' ORDER BY id DESC LIMIT 1") && EXT=$(echo "$MIME" | sed 's|image/||; s|application/pdf|pdf|') && sqlite3 ~/.local/share/opencode/opencode.db "SELECT json_extract(data,'$.url') FROM part WHERE json_extract(data,'$.mime')='$MIME' ORDER BY id DESC LIMIT 1" | sed 's/^data:[^;]*;base64,//' | base64 -d > "/tmp/opencode-inline.$EXT" && echo "/tmp/opencode-inline.$EXT"
```

## Current Config

Agent models per preset: `~/.config/opencode/oh-my-opencode-slim.json` (read directly, don't hardcode).
