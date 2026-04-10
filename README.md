# Occam's Code

> OpenCode setup sharpened by Occam's Razor.

> The simplest solution that fully solves the problem is the correct solution.

A shareable, open-source configuration for [OpenCode](https://github.com/sst/opencode) — an AI coding agent with multi-model orchestration, Karpathy-style persistent wiki memory, and a smart launcher.

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, agent model tweaker, memory sync, project initialization, health checks, and permission toggles
- **4 presets** — `balanced` (default), `cheap`, `premium`, `zai-coding-plan` (subscription)
- **10 Python scripts** — Memory sync, model optimizer, config generator, project init, provider health, repo ingestion, wiki lint, and more
- **5 slash commands** — `/preset`, `/wiki`, `/remember`, `/wiki-lint`, `/permissions`
- **oh-my-opencode-slim** config — 6 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **4 MCP servers** — context7 (library docs), grep_app (code search), semantic_search (local index), websearch (Exa)
- **9 skills** — agent-browser, code-review, defuddle, obsidian-cli, obsidian-markdown, obsidian-bases, json-canvas, simplify, pr-integration
- **Karpathy-style wiki** — Persistent knowledge base (raw → wiki one-way compile), Obsidian-compatible
- **AGENTS.md** — 8 workflow principles for AI agents: divide & conquer, plan first, wiki-first, keep wiki alive, ask questions, parallel execution, minimize waste, Occam's Code

## Quick Start

### Prerequisites

- [OpenCode](https://github.com/sst/opencode) installed (`npm install -g opencode` or `bun install -g opencode`)
- Python 3.10+
- Bash 4.0+ (Linux: default. macOS: `brew install bash`)
- [jq](https://stedolan.github.io/jq/), [fzf](https://github.com/junegunn/fzf)
- API keys for at least one provider (OpenRouter, Anthropic, or Z.AI)

### Install

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code
./scripts/install.sh
```

The installer will:
1. Copy scripts, commands, and config to `~/.config/opencode/`
2. Copy the wiki template to `~/wiki/`
3. Generate `opencode.json` with your home directory paths
4. Install oh-my-opencode-slim plugin

See [INSTALL.md](INSTALL.md) for detailed per-platform instructions.

### First Launch

```bash
oc                  # Interactive: pick preset → tweak agents → launch
oc --preset cheap   # Skip prompts, use cheap preset
oc --doctor         # Check everything is set up correctly
```

## Usage

### The `oc` Launcher

```
oc                    Full interactive mode (preset → agents → launch)
oc --quick            Pick preset only, skip agent tweaking
oc --preset <name>    Use preset directly (balanced/cheap/premium/zai-coding-plan)
oc --memory-sync      Sync project + wiki memory (incremental)
oc --sync-fast        Fast sync (project only)
oc --sync-full        Full reindex (project + wiki)
oc --init-project     Create project wiki page + bootstrap project memory
oc --doctor           Run integration health checks
oc --unsafe           Auto-approve all permissions for this session
oc --safe             Enable permission prompts for this session
oc --ingest-repo URL  Snapshot GitHub repo into wiki
oc -c                 Continue last session
oc --lint-wiki        Run wiki content health check
oc --sync-config      Sync AGENTS.md model table from config
```

### Permissions

Default is `--unsafe` (auto-approve). We trust you. You trust your agents. Life's too short for permission dialogs.

To make prompts the default, remove `"permission": "allow"` from `~/.config/opencode/opencode.json`. Then use `oc --unsafe` when you want to live dangerously.

### The Wiki

The wiki at `~/wiki/` follows Karpathy's LLM Wiki pattern:

- **`raw/`** — Immutable source documents (articles, repos, papers). Never modify.
- **`wiki/`** — LLM-generated knowledge base (summaries, concepts, patterns, project pages)
- **`AGENTS.md`** — Schema that tells the LLM how to maintain the wiki

Open `~/wiki/` in [Obsidian](https://obsidian.md) for the best experience. The LLM maintains all content — you provide sources and curate.

### Agents

6 specialist agents, each with curated models per preset:

| Agent | Role | Delegation trigger |
|-------|------|--------------------|
| **orchestrator** | Main agent, delegates to specialists | — (this is you) |
| **@oracle** | Architecture, code review, complex debugging | High-stakes decisions, persistent bugs |
| **@fixer** | Fast implementation, test writing | Bounded tasks, multi-file changes |
| **@designer** | UI/UX, responsive layouts, visual polish | User-facing interfaces |
| **@explorer** | Parallel codebase search | Finding files before reading them |
| **@librarian** | Library docs, API references | Version-specific behavior, unfamiliar APIs |

### Council

Multi-LLM consensus for high-stakes decisions. Runs multiple models in parallel and synthesizes their responses.

### MCP Servers

| Server | Purpose |
|--------|---------|
| **context7** | Remote library documentation lookup |
| **grep_app** | Search code across open-source repos |
| **semantic_search** | Local project code index (sentence-transformers) |
| **websearch** (Exa) | Web search for current information |

## 8 Workflow Principles

1. **Divide and Conquer** — Parallel subtasks via agents
2. **Plan Before Execute** — Present plan, get feedback, then execute
3. **Wiki-First Knowledge** — Check wiki before starting any task
4. **Keep Wiki Alive** — Stale wiki is worse than no wiki
5. **Ask Questions** — Uncertainty → ask before proceeding
6. **Parallel Agent Execution** — Fire multiple searches/agents concurrently
7. **Minimize Waste** — Be terse, no filler, caveman-style communication
8. **Occam's Code** — Simplest solution that fully solves the problem wins

## Autonomous Mode

Want to step away and let the agent work? Use `/auto-continue on` (built into oh-my-opencode-slim).

The agent will keep working through incomplete TODOs without stopping. It stops when:
- All TODOs are completed
- It asks you a question
- You press Esc
- Max iterations reached (configurable, default 50)

**Best practice:** Write a design doc with clear TODOs before enabling. Descriptive TODOs help the agent recover context after long sessions.

**Example workflow:**
```
/remember → "Write design doc with TODOs"
/auto-continue on
# ... go make coffee, come back to finished work
```

## Directory Structure

```
~/.config/opencode/
├── AGENTS.md                      # Agent rules and workflow principles
├── opencode.json                  # Core config (generated by generate-config.py)
├── oh-my-opencode-slim.json       # Presets, agents, fallback chains, council
├── bin/oc                         # Launcher script
├── scripts/                       # Python utilities (10 scripts)
└── commands/                      # Slash command definitions (5 commands)

~/wiki/
├── AGENTS.md                      # Wiki schema (LLM follows these rules)
├── index.md                       # Master routing table
├── log.md                         # Append-only activity log
├── overview.md                    # High-level wiki synthesis
├── raw/                           # Immutable source documents
│   ├── articles/  papers/  repos/ docs/  forums/  assets/  _inbox/
└── wiki/                          # LLM-generated knowledge base
    ├── projects/  domain/  languages/ patterns/
    ├── concepts/  entities/  sources/  comparisons/
```

## License

MIT — see [LICENSE](LICENSE).
