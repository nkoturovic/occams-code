# OpenCode — Agent Rules & Setup

## Session Rules
- Wait for the user's first message before doing anything.
- On your **first response** in a session, check `~/wiki/index.md` for relevant project pages and knowledge. If the current project or topic has a wiki page, read it and apply that context silently (don't narrate it unless asked). If relevant conventions, patterns, or prior decisions exist in the wiki, use them.
- If this is an unfamiliar project (no wiki page, not your own repo), check for instruction files the project may have: `CLAUDE.md`, `.github/copilot-instructions.md`, `.copilot/`, `.cursorrules`, `.windsurfrules`, or similar. Read them if found — they contain project conventions. Our `AGENTS.md` takes precedence on conflicts.
- Use semantic_search only as a secondary fallback, not automatically.
- Keep changes traceable and update wiki/log when durable knowledge is produced.
- Respond in English unless the user asks otherwise.
- **Never push, upload, post, or transmit** code, files, or data to any external service, URL, or API without explicit user approval. This includes `git push`, `curl POST`, file uploads, and any network operation that sends data outbound. Local file reads, command execution, and tool usage are fine.

## Workflow Principles

### 1. Divide and Conquer
- Break tasks into independent subtasks that can execute in parallel via agents.
- Use TODOs to track decomposition — `todowrite` is visible in OpenCode's UI.
- Prefer 3 parallel fixer tasks over 1 sequential mega-task.
- Council runs councillors in **parallel** (not serial).

### 2. Plan Before Execute
- Invest substantial time in planning before writing code.
- Present the plan to the user for review before executing.
- Ask clarifying questions early — uncertainty compounds with parallel execution.
- A good plan makes parallel execution safe; a bad plan makes it chaotic.

### 3. Wiki-First Knowledge
- Check `~/wiki/index.md` and project pages **before** starting any task.
- Apply existing conventions, patterns, and decisions from wiki.
- When discovering stable facts, **proactively** persist them to wiki (don't wait to be asked).
- Keep wiki organized and up-to-date — it compounds in value over time.

### 4. Keep Wiki Alive *(knowledge continuity)*
**This is not optional — stale wiki is actively harmful.**
- Wiki is **not** a write-once artifact. Update it **continuously** during every session.
- Proactively persist: new findings, changed decisions, updated conventions, failure modes, build commands.
- Stale wiki is worse than no wiki — it misleads. If something changed, update the page immediately.
- Run `/wiki-lint` periodically to catch orphans, broken links, and stale claims.
- Append to `~/wiki/log.md` on every meaningful change.

### 5. Ask Questions
- Any uncertainty or ambiguity → ask the user before proceeding.
- Better to ask too many questions upfront than to execute the wrong plan in parallel.
- When presenting options, state your recommendation and why.

### 6. Parallel Agent Execution
- Use `ultrawork` or `ulw` in prompts for parallel agent dispatch.
- Delegate to specialists (`@explorer`, `@fixer`, `@librarian`) — they run concurrently.
- Fire multiple searches in parallel before reading files.
- Combine results after parallel work completes.

### 7. Minimize Waste *(communication & operations)*
- **Be terse.** Drop filler, keep technical accuracy. "Segfault on null ptr. Add guard." beats a paragraph saying the same thing.
- Don't re-read files you already have in context.
- Don't narrate wiki contents — apply silently.
- Keep AGENTS.md concise — models prioritize content at the top.
- One-word answers are fine when appropriate.
- Compress wiki pages when they grow verbose — preserve human-readable originals alongside compressed versions if needed.

### 8. Occam's Code *(solution design)*
**The simplest solution that fully solves the problem is the correct solution.**
- Fewest changes. Fewest files. Fewest abstractions.
- If two approaches work equally, the shorter wins.
- Every abstraction, file, and line must earn its place — nothing exists without necessity.
- The ideal solution is monadic: indivisible, irreducible, complete.

## How memory works (for the agent)
1. **Wiki** lives at `~/wiki/`. Read `~/wiki/index.md` first — it's the routing table to all project pages, conventions, patterns, etc.
2. **Per-project pages** are at `~/wiki/wiki/projects/<slug>.md`. Match the current working directory to a project page by looking for the `Path:` field inside pages. If no exact match, check if the cwd is a subdirectory of a known project path.
3. **Conventions and patterns** are at `~/wiki/wiki/languages/`, `~/wiki/wiki/patterns/`, etc. The index links to them. If the project or task relates to a known language/pattern, read it.
4. **Session memory update**: when you discover stable facts, **proactively** persist them. Don't wait to be asked. Route to the right place:
   - **Per-project** → `~/wiki/wiki/projects/<slug>.md` — architecture decisions, build/test commands, failure modes, gotchas specific to this project
   - **Language/pattern** → `~/wiki/wiki/languages/<lang>.md` or `~/wiki/wiki/patterns/<name>.md` — reusable conventions, idioms, patterns that apply across projects. Create new pages if none exist.
   - **Global** → `~/wiki/wiki/concepts/` or `~/wiki/wiki/entities/` — tools, services, general knowledge worth remembering across all work
   - **Always** → append to `~/wiki/log.md` with date, project, and what changed
   - **Always** → update `~/wiki/index.md` if you created a new page
   - Update the `updated:` field in frontmatter when editing a wiki page.
5. **semantic_search** MCP can search indexed project code. Use it as a secondary lookup when wiki doesn't have the answer.

## Current Config

**4 presets:** `balanced` (default) → `cheap` → `premium` → `zai-coding-plan`

| Agent | Balanced | Cheap | Premium | Zai-coding-plan |
|-------|----------|-------|---------|-----------------|
| orchestrator | qwen/qwen3.6-plus | qwen/qwen3-coder | claude-opus-4-6 | glm-5.1 |
| oracle | claude-sonnet-4-6 | deepseek/deepseek-v3.2 | claude-opus-4-6 | glm-5.1 |
| fixer | z-ai/glm-5.1 | deepseek/deepseek-v3.2 | claude-opus-4-6 | glm-5.1 |
| designer | google/gemini-3.1-flash-lite-preview | google/gemini-3-flash-preview | google/gemini-3.1-pro-preview | glm-5.1 |
| explorer | nvidia/nemotron-3-super-120b-a12b:free | nvidia/nemotron-3-super-120b-a12b:free | claude-sonnet-4-6 | glm-5.1 |
| librarian | qwen/qwen3.6-plus | nvidia/nemotron-3-super-120b-a12b:free | claude-sonnet-4-6 | glm-5.1 |

**Fallback chains:** 5 entries each, quality → cost gradient, auto-trigger on 60s timeout.

## Memory System

Two-layer persistent memory keeps context across sessions:

1. **Global + project wiki memory** — `~/wiki` (Karpathy-style markdown KB; each project gets its own page in `wiki/projects/` plus shared global pages)
2. **Project semantic memory** — index in `~/.opencode_memory/projects/*` (auto-built by semantic_search backend)

**Retrieval order (wiki-first):**
1) `~/wiki/index.md` + project page
2) semantic project index (`semantic_search`)
3) external docs/web only when needed

## Quick Start

```
oc              # Interactive launcher (preset → agents → launch)
oc --quick      # Pick preset, skip agent tweaks
oc --preset cheap   # Direct launch with preset (new session implied)
oc --memory-sync    # Standard sync (project + wiki, incremental)
oc --sync-fast      # Fast memory sync (project only, incremental)
oc --sync-full      # Full memory sync (project + wiki, non-incremental)
oc --sync-config    # Sync AGENTS.md model table from config
oc --init-project   # Create wiki page + bootstrap project memory
oc --doctor         # Run integration health checks
oc --unsafe        # Auto-approve all permissions for one session (default behavior)
oc --safe          # Enable permission prompts for one session
oc --ingest-repo URL # Snapshot GitHub repo into wiki raw/sources
oc -c           # Continue last session
```

## Slash Commands (type / or Ctrl+P)

| Command | What it does |
|---------|-------------|
| `/preset` | Show active preset and agent models |
| `/permissions` | Show permission modes (`--safe` / `--unsafe`) |
| `/wiki` | Show project wiki and relevant knowledge |
| `/remember` | Persist session knowledge to wiki |
| `/wiki-lint` | Run wiki content health check |
| `/models` | Change model for current agent (built-in) |
| `/init` | Guided AGENTS.md setup (built-in) |
| `/review` | Review uncommitted changes (built-in) |

## Typical Workflow

1. **Launch**: `oc` → pick session (new/continue) → pick preset → launch
2. **Start working**: agent reads wiki automatically on first response
3. **During session**: `/wiki` to check context, `/models` to swap current agent model, `/wiki-lint` to check wiki health
4. **After discovery**: `/remember` to save what you learned (or agent does it proactively)
5. **End session**: knowledge persists in wiki for next session

## Working Tips
- **Use `ultrawork` or `ulw`** in prompts for parallel agent execution
- **Start with `balanced` preset**, switch to `cheap` for exploration, `premium` for critical work
- **Delegate to specialists** — don't do everything in one agent
- **Explorer first** — find files before reading them
- **Check budget** periodically: `python3 ~/.config/opencode/scripts/model-optimizer.py --budget`

## Providers

| Provider | Models | Auth |
|----------|--------|------|
| openrouter | 400+ models (pay-per-token primary) | auth.json |
| anthropic | claude-* (direct API) | auth.json |
| zai-coding-plan | GLM-5.1, GLM-5, GLM-5-turbo, GLM-4.7, GLM-4.5-air (subscription) | auth.json |

## Council

Multi-LLM consensus for high-stakes decisions. Runs councillors in **parallel**, master synthesizes.

| Council Preset | Master | Councillors |
|---------------|--------|-------------|
| default (balanced) | claude-sonnet-4-6 | sonnet + qwen × 2 |
| cheap | deepseek-v3.2 | deepseek + qwen-coder × 2 |
| premium | claude-opus-4-6 | opus + sonnet × 2 |
| zai-coding-plan | glm-5.1 | glm-5.1 × 3 |

## Troubleshooting

- **Agents not working:** `opencode models --refresh`, check auth status
- **LSP broken:** verify server installed (`which clangd`, etc.)
- **Cost too high:** `oc --preset cheap` or run optimizer to find savings
- **Semantic memory issues:** `python3 ~/.config/opencode/scripts/memory-sync.py --list` and rerun `oc --memory-sync`
