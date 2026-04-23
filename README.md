# Occam's Code

> OpenCode setup sharpened by Occam's Razor.

> The simplest solution that fully solves the problem is the correct solution.

A shareable, open-source configuration for [OpenCode](https://github.com/sst/opencode) — an AI coding agent with multi-model orchestration, Karpathy-style persistent wiki memory, and a smart launcher.

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, project initialization, health checks, and permission toggles
- **4 presets** — `balanced` (default), `cheap`, `premium`, `custom` (subscription-based)
- **4 Python scripts** — Wiki lint, project init, repo ingestion, project state detection
- **4 slash commands** — `/preset`, `/wiki`, `/remember`, `/permissions` (plus `/auto-continue` from oh-my-opencode-slim)
- **oh-my-opencode-slim** config — 7 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **3 MCP servers** — context7 (library docs), grep_app (code search), zai_vision (image analysis, opt-in). Plus websearch (Exa) built-in to plugin
- **9 skills** — agent-browser, code-review, defuddle, obsidian-cli, obsidian-markdown, obsidian-bases, json-canvas, simplify, pr-integration
- **Karpathy-style wiki** — Persistent knowledge base (raw → wiki one-way compile), Obsidian-compatible
- **AGENTS.md** — 6 workflow principles for AI agents, ordered by criticality

## Quick Start

### Prerequisites

- [OpenCode](https://github.com/sst/opencode) installed (`npm install -g opencode` or `bun install -g opencode`)
- Python 3.10+, Bash 4.0+, [jq](https://stedolan.github.io/jq/), git, curl
- `npm` or `bun` (for oh-my-opencode-slim plugin)
- API keys for at least one provider (OpenRouter, Anthropic, or Z.AI)
- *Optional:* [fzf](https://github.com/junegunn/fzf) for interactive preset picker

<details>
<summary>Platform-specific notes</summary>

- **Linux:** bash 4+ is default. `sudo apt install python3 jq git curl` (Debian/Ubuntu)
- **macOS:** `brew install bash jq` (bash 5 required, system bash 3.2 won't work with `oc`)
- **Windows:** Use WSL2, then same as Linux

</details>

### Install

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code
./scripts/install.sh
```

The installer will:
1. Copy scripts, commands, and config to `~/.config/opencode/`
2. Copy the wiki template to `~/wiki/`
3. Copy `opencode.json` core config
4. Install oh-my-opencode-slim plugin

See [INSTALL.md](INSTALL.md) for detailed per-platform instructions.

### First Launch

```bash
oc                  # Interactive: pick preset, launch
oc --preset cheap   # Skip prompts, use cheap preset
oc --doctor         # Check everything is set up correctly
```

## Usage

### The `oc` Launcher

```
oc                  Interactive launch (first run picks preset)
oc --quick          Skip prompts, use project/global config directly
oc --preset <name>  Set preset, create project config, launch
oc --doctor         Run diagnostics (config, wiki, lint)
oc --init-project   Create project wiki page + AGENTS.md
oc --ingest-repo URL  Snapshot GitHub repo into wiki
oc -c               Continue last session
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

### Presets

| Preset | Use case | Cost model |
|--------|----------|------------|
| `cheap` | Quick tasks, exploration | Free/cheap models only |
| `balanced` | Daily development | Mix of quality and cost |
| `premium` | Complex architecture, debugging | Best models regardless of cost |
| `custom` | **Subscription-based** — mirrors the live setup's Kimi+GLM allocation | Requires Kimi for Coding ($39/mo) and Z.AI Coding Plan ($30/mo) |

**Note:** The `custom` preset uses `kimi-for-coding/` and `zai-coding-plan/` providers that require active subscriptions. If you don't have these, use `balanced` or `premium` instead.

### Per-Project Config

The `oc` launcher creates `.opencode/oh-my-opencode-slim.json` in your project root on first run. Override preset or individual agent models:

```json
{ "preset": "cheap" }
```

```json
{
  "presets": {
    "balanced": {
      "oracle": { "model": "anthropic/claude-sonnet-4-6" }
    }
  }
}
```

Vision-enabled observer (needs multimodal model + `zai_vision` MCP for video fallback):

```json
{
  "presets": {
    "balanced": {
      "observer": { "model": "openrouter/moonshotai/kimi-k2.6" }
    }
  }
}
```

The plugin deep-merges project config with global config. Edit the file directly — no wizard needed. `.opencode/` is gitignored.

### Scripts

| Script | Purpose |
|--------|---------|
| `wiki-lint.py` | Wiki health check (dead links, orphans, stale pages) |
| `project-init.py` | Creates wiki page + project AGENTS.md |
| `repo-ingest.py` | Snapshots GitHub repo into wiki |
| `detect-project-state.py` | Project state detection (used by --doctor) |

### Agents

7 specialist agents, each with curated models per preset:

| Agent | Role | Delegation trigger |
|-------|------|--------------------|
| **orchestrator** | Main agent, delegates to specialists | — (this is you) |
| **@oracle** | Architecture, code review, complex debugging | High-stakes decisions, persistent bugs |
| **@fixer** | Fast implementation, test writing | Bounded tasks, multi-file changes |
| **@observer** | Visual analysis: images, PDFs, video → text facts | File-on-disk visual content |
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
| **zai_vision** | Image analysis, UI-to-code, OCR, diagrams, video (opt-in, needs Z.ai API key) |

**Built-in:** websearch (Exa) — provided by oh-my-opencode-slim plugin, no config needed.

## Workflow Principles

1. **Occam's Code** — Simplest solution that fully solves the problem wins
2. **Ask Questions** — Uncertainty → ask before proceeding; present plans for review
3. **Divide and Conquer** — Break into independent parallel subtasks
4. **Parallelize** — Delegate to specialist agents, run concurrently
5. **Wiki** — Check wiki before starting, update it continuously
6. **Be Terse** — No filler, caveman-style communication

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
├── opencode.json                  # Core config
├── oh-my-opencode-slim.json       # Presets, agents, fallback chains, council
├── bin/oc                         # Launcher script
├── scripts/                       # Python utilities (4 scripts)
└── commands/                      # Slash command definitions (4 commands)

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
