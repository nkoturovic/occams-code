# OpenCode — Agent Rules & Setup

## Session Rules
- Wait for the user's first message before doing anything.
- **On session start**, read `~/wiki/index.md` to discover available project pages and knowledge. Apply relevant context silently (don't narrate it unless asked). **Throughout the session**, consult wiki before starting any task — not just at the start.
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

### 8. Occam's Code *(solution design)*
**The simplest solution that fully solves the problem is the correct solution.**
- Fewest changes. Fewest files. Fewest abstractions.
- If two approaches work equally, the shorter wins.
- Every abstraction, file, and line must earn its place — nothing exists without necessity.
- The ideal solution is monadic: indivisible, irreducible, complete.

## How memory works (for the agent)
1. **Wiki** lives at `~/wiki/`. Read `~/wiki/index.md` first — it's the routing table to all project pages, conventions, patterns, etc.
2. **Per-project pages** are at `~/wiki/wiki/projects/<slug>.md`. Match the current working directory to a project page by looking for the `Path:` field inside pages.
3. **Conventions and patterns** are at `~/wiki/wiki/languages/`, `~/wiki/wiki/patterns/`, etc.
4. **Session memory update**: when you discover stable facts, **proactively** persist them. Route to the right place:
   - **Per-project** → `~/wiki/wiki/projects/<slug>.md`
   - **Language/pattern** → `~/wiki/wiki/languages/<lang>.md` or `~/wiki/wiki/patterns/<name>.md`
   - **Global** → `~/wiki/wiki/concepts/` or `~/wiki/wiki/entities/`
   - **Always** → append to `~/wiki/log.md` with date, project, and what changed
   - **Always** → update `~/wiki/index.md` if you created a new page
5. **Project semantic memory** — index in `~/.opencode_memory/projects/*` (auto-built by semantic_search backend). Use as secondary lookup when wiki lacks the answer.
6. **Retrieval order:** wiki first → semantic index → external docs/web.

## Agent Types & Delegation

| Agent | When to delegate | Key capability |
|-------|-----------------|----------------|
| **@explorer** | Discover files/symbols before reading | Glob, grep, AST — 3x faster search |
| **@fixer** | Bounded implementation, test writing | 2x faster edits |
| **@librarian** | Library docs, API references | 10x better at current APIs |
| **@oracle** | Architecture, code review, complex debugging | Deep reasoning, trade-offs |
| **@designer** | UI/UX, responsive layouts, visual polish | 10x better UI/UX |
| **@council** | Critical decisions needing diverse perspectives | Multi-LLM consensus |

**Don't delegate** when: single small change (<20 lines), you already have the file, or explaining > doing.

## Tools Reference

| Category | Tool | When to use |
|----------|------|-------------|
| Tracking | `todowrite` | Task decomposition (visible in UI, update proactively) |
| Tracking | `auto_continue` | Batch work (4+ todos) — orchestrator resumes automatically |
| Parallel | `background_task` / `_output` / `_cancel` | Fire-and-forget parallel agents (up to 10 concurrent) |
| Consensus | `council_session` | Multi-LLM consensus — councillors in parallel, master synthesizes |
| Code | `ast_grep_search` / `ast_grep_replace` | Structured search/replace (25 langs). Prefer over regex |
| Code | `lsp_diagnostics` | Errors/warnings *before* build. Use after writing code |
| Code | `lsp_goto_definition` / `lsp_find_references` | Navigate code |
| Code | `lsp_rename` | Safe rename across workspace |
| MCP | **context7** — library docs (auto-triggered by @librarian) |
| MCP | **grep_app** — open-source code search (real-world API patterns) |
| MCP | **semantic_search** — local project code index (secondary lookup) |
| MCP | **websearch** (Exa) — web search (docs, news, facts) |
| Skill | **agent-browser** — web automation, screenshots, scraping |
| Skill | **code-review** — structured code review, security audit |
| Skill | **simplify** — code cleanup after writing |
| Skill | **pr-integration** — GitHub PR create/review |
| Skill | **defuddle** — clean markdown from web pages |
| Skill | **obsidian-cli/markdown/bases** — Obsidian vault operations |
| Skill | **json-canvas** — visual canvases, mind maps |

Skills 1–4 are bundled with OpenCode. Skills 5–7 require [obsidian-skills](https://github.com/kepano/obsidian-skills) (`install.sh` installs automatically).

## Current Config

**4 presets:** `balanced` (default) → `cheap` → `premium` → `zai-coding-plan`
Agent models per preset: `~/.config/opencode/oh-my-opencode-slim.json` (read directly, don't hardcode).
**Fallback chains:** 5 entries each, quality → cost gradient, 60s timeout.
**Permissions:** `--unsafe` (default) / `--safe` (temporary prompts for one session).

## Council

Multi-LLM consensus for high-stakes decisions. Parallel councillors, master synthesizes.
Default (balanced): see oh-my-opencode-slim.json for master/councillors per preset.

## Providers

| Provider | Models | Auth |
|----------|--------|------|
| openrouter | 400+ models (pay-per-token) | auth.json |
| anthropic | claude-* (direct API) | auth.json |
| zai-coding-plan | GLM-5.1, GLM-5, GLM-5-turbo, GLM-4.7, GLM-4.5-air (subscription) | auth.json |

## Slash Commands

| Command | What it does |
|---------|-------------|
| `/preset` | Show active preset and agent models |
| `/permissions` | Show permission modes (`--safe` / `--unsafe`) |
| `/auto-continue` | Toggle autonomous mode (`on` / `off`) — agent keeps working through TODOs |
| `/wiki` | Show project wiki and relevant knowledge |
| `/remember` | Persist session knowledge to wiki |
| `/wiki-lint` | Run wiki content health check |
