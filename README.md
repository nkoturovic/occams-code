# Occam's Code

> OpenCode integration layer for [occams-agentic](https://github.com/nkoturovic/occams-agentic) — sharpened by Occam's Razor.
> *The simplest solution that fully solves the problem is the correct solution.*

The OpenCode-specific configuration layer for the [occams-agentic](https://github.com/nkoturovic/occams-agentic) AI framework. Provides multi-model orchestration, a smart launcher (`oc`), and curated agent presets on top of the universal skills, scripts, and wiki from occams-agentic.

**The default `balanced` and budget `cheap` presets work fully with just an OpenRouter API key.** Other presets unlock additional capabilities if you have Anthropic / DeepSeek / Z.AI / Kimi keys or OpenAI OAuth, but you don't need them to start.

## Quick Start

```bash
# 1. Install occams-agentic (universal layer)
git clone https://github.com/nkoturovic/occams-agentic.git && cd occams-agentic
./bin/bootstrap.sh

# 2. Install occams-code (OpenCode layer)
cd .. && git clone https://github.com/nkoturovic/occams-code.git && cd occams-code
./scripts/install.sh                                    # interactive
```

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, project initialization, health checks, and permission toggles
- **6 presets** — `balanced` (default) and `cheap` are OpenRouter-only; `deepseek`, `premium`, `custom`, and `openai` use additional providers
- **6 OpenCode scripts** — Config generator, model health check, project init, state detection, log cleanup, interactive installer
- **6 slash commands** — `/preset`, `/wiki`, `/remember`, `/permissions`, `/wiki-lint`, `/model-switch` (plus `/auto-continue` from oh-my-opencode-slim)
- **oh-my-opencode-slim** plugin — 7 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **model-profile.jsonc** — Model-mapping source of truth. Edit, run `oc --sync-profile` to regenerate oh-my-opencode-slim.json, restart. Per-agent MCP/skill assignments live in oh-my-opencode-slim.json (committed preset). Plus per-project overrides via `.opencode/oh-my-opencode-slim.jsonc`
- **5 MCP servers** — context7 (library docs), gh_grep (grep.app code search), websearch (Exa), zai_vision (image analysis), and web-search-prime (Z.AI web search). Z.AI MCPs require `Z_AI_API_KEY`.
- **3 OpenCode skills** — codemap, simplify, clonedeps (universal skills like audio-analysis, video-analysis, lecture-notes come from occams-agentic)

### Prerequisites

- [**occams-agentic**](https://github.com/nkoturovic/occams-agentic) — must be installed first (provides `~/.agents/` with skills, scripts, and wiki)
- [OpenCode](https://github.com/sst/opencode) (`npm install -g opencode` or `bun install -g opencode`)
- Python 3.10+, Bash 4.0+, [jq](https://stedolan.github.io/jq/), git, curl
- `npm` or `bun` (for installing the oh-my-opencode-slim plugin)
- An OpenRouter API key for the out-of-box `balanced` or `cheap` preset; additional providers are optional

<details>
<summary>Platform-specific notes</summary>

- **Linux:** bash 4+ is default. `sudo apt install python3 jq git curl` (Debian/Ubuntu) / `brew install jq` (others)
- **macOS:** `brew install bash jq` — system bash 3.2 won't run `oc`. After install, run with `/opt/homebrew/bin/bash` or `chsh -s /opt/homebrew/bin/bash`.
- **Windows:** Use WSL2 — same as Linux from inside WSL.

</details>

### Install

```bash
git clone https://github.com/nkoturovic/occams-code.git && cd occams-code
./scripts/install.sh                                          # interactive (recommended)
```

The installer:

1. Copies OpenCode-specific scripts, commands, configs, AGENTS.md to `~/.config/opencode/`
2. Installs the oh-my-opencode-slim plugin
3. Sets up API keys (interactively, shell-visible in `~/.config/secrets/env`)

> **Note:** `~/.agents/` (skills, scripts, wiki) is set up by occams-agentic's `bootstrap.sh` — run that first.

Set up your API keys in `~/.local/share/opencode/auth.json` and `~/.config/secrets/env`. See [INSTALL.md](INSTALL.md) for the full reference and manual install instructions.

### First Launch

```bash
oc --doctor              # Verify config + wiki health
oc                       # Interactive: pick preset, launch
oc --preset cheap        # Skip prompts, use the cheap preset
oc --sync-profile        # Regenerate oh-my-opencode-slim.json from model-profile.jsonc
```

## Usage

### The `oc` Launcher

```
oc                  Interactive launch (first run picks preset)
oc --quick          Skip prompts, use project/global config directly
oc --no-init        Skip project config setup and workspace init
oc --preset <name>  Set preset, create project config, launch
oc --doctor         Run diagnostics (config, wiki, lint)
oc --sync-profile    Regenerate config from model-profile.jsonc
oc --init-project   Create project wiki page + AGENTS.md + project .agents workspace
oc --ingest-repo URL  Snapshot GitHub repo into wiki
oc -c               Continue last session
```

Project workspace init (`AGENTS.md` + `.agents/` + wiki page) asks for confirmation in interactive mode. It defaults to yes (`[Y/n]`) for normal directories, including empty folders with sensible names, and defaults to no (`[y/N]`) only for obvious temp/scratch dirs. `--quick` keeps non-prompting auto-init behavior when a project config already exists; `--no-init` disables both project config setup and workspace init.

### Permissions

By default `opencode.json` ships with `"permission": "allow"` — the agent auto-approves every tool call. This is good for trusted local work; not great for code you didn't write yourself.

- `oc --safe` — temporarily switches to permission prompts for the current session (restored on exit).
- To make prompts the persistent default, remove `"permission": "allow"` from `~/.config/opencode/opencode.json`. Then use `oc --unsafe` for one-off auto-approve sessions.

### The Wiki

The wiki at `~/.agents/wiki/` follows Karpathy's LLM Wiki pattern:

- **`raw/`** — Immutable source documents (articles, repos, papers). Never modify.
- **topic directories** — LLM-generated knowledge base (`concepts/`, `patterns/`, `projects/`, etc.)
- **`AGENTS.md`** — Schema that tells the LLM how to maintain the wiki

Open `~/.agents/wiki/` in [Obsidian](https://obsidian.md) for the best experience. The LLM maintains all content — you provide sources and curate.

### Presets

| Preset | Use case | Primary-route access | Notes |
|--------|----------|----------------------|-------|
| `balanced` | **Default** — daily development | OpenRouter only | DeepSeek V4 Pro (orchestrator/oracle/fixer/council), Nemotron Free (explorer/librarian), Gemini 3.5 Flash (designer/observer); all fallbacks also use OpenRouter |
| `cheap` | Exploration, bulk tasks | OpenRouter only | Qwen3-Coder Free (orchestrator/fixer), DeepSeek V4 Pro (oracle), Nemotron Free (explorer/librarian/council), Gemini 3.5 Flash (designer/observer); all fallbacks also use OpenRouter |
| `deepseek` | DeepSeek-heavy reasoning | DeepSeek API + Z.AI + OpenRouter | DeepSeek V4 Pro (orchestrator/oracle/librarian/council), GLM-5.2 (explorer/fixer), Gemini 3.5 Flash (designer/observer) |
| `premium` | Complex architecture, debugging | Anthropic + OpenRouter | Claude Opus 4.7 (orchestrator/oracle/council), Claude Sonnet 4.6 (explorer/librarian/fixer), Gemini 3.5 Flash (designer/observer) |
| `custom` | Subscription-based | Z.AI + OpenAI OAuth + Kimi + DeepSeek | GLM-5.2 (orchestrator/librarian/fixer), GPT-5.6 Sol (oracle), GPT-5.6 Terra (explorer), Kimi K2.7 Code (designer/observer), DeepSeek V4 Pro (council) |
| `openai` | OpenAI-first via OAuth | OpenAI OAuth (`/connect`) | GPT-5.6 Sol (orchestrator/oracle/fixer/council), GPT-5.6 Terra (explorer/librarian/designer/observer) |

**The default `balanced` and budget `cheap` presets work fully with just an OpenRouter key.** The other presets require additional API keys or subscriptions for their primary routes.

### Per-Project Config

The `oc` launcher creates `.opencode/oh-my-opencode-slim.jsonc` (preferred, supports comments) or `.json` in your project root on first run. Override preset or individual agent models:

Switch preset:
```jsonc
{ "preset": "cheap" }
```

Switch one agent's model (recommended — explicit temperature):
```jsonc
{
  "agents": {
    "orchestrator": {
      "model": "deepseek/deepseek-v4-pro",
      "variant": "max",
      "temperature": 1.0
    }
  }
}
```

**Important:** Always set `temperature` explicitly when switching models — otherwise the preset's temperature (tuned for the original model) leaks through. See the annotated template in this repo for full documentation.

**Deep-merge gotchas:**
- Omitted keys inherit from global config — set only what you want to change
- Arrays (`skills`, `mcps`, `disabled_agents`) are **replaced entirely**, not appended — list all desired values
- Nested objects (`options`) merge recursively — you cannot unset keys by omission
- oh-my-opencode-slim v2.1.0 deep-merges project `presets` with user presets, so project configs can override a single preset/agent without redefining every preset

The plugin deep-merges project config with global config. Edit the file directly — no wizard needed. `.opencode/` is gitignored.

### Continuing Old Sessions After Config Changes

> ⚠️ When you continue an old session (via startup prompt or `/sessions`), OpenCode restores the model from the session's **last user message**, overriding your current config. Subagents are unaffected — they always use the current config.

**Workaround:** After continuing an old session, use `/models` to select the correct model. Temperature and options are always from the current config — only the model ID needs fixing. Alternatively, start a new session instead.

### Scripts

OpenCode-specific scripts (universal scripts like `project-init.py`, `transcribe`, `analyze-video.py`, `wiki-lint.py`, `lecture-*.py`, and `repo-ingest.py` are provided by occams-agentic at `~/.agents/scripts/`):

| Script | Purpose |
|--------|---------|
| `model-profile.py` | **Config generator** — regenerates model assignments in oh-my-opencode-slim.json from model-profile.jsonc (per-agent MCP/skill config is in the committed preset) |
| `doctor-model-check.py` | Model health check — verifies API connectivity and model availability (used by `--doctor`) |
| `project-init.py` | Compatibility wrapper → `~/.agents/scripts/project-init.py` |
| `detect-project-state.py` | Project state detection (reads `.opencode/` — used by `--doctor`) |
| `cleanup-logs.sh` | Weekly cleanup for OpenCode core and oh-my-opencode-slim logs |
| `install.sh` | Interactive installer for the occams-code layer |

### Agents

1 orchestrator + 6 specialist agents, each with curated models per preset:

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

**Default (3, always enabled):**

| Server | Purpose |
|--------|---------|
| **context7** | Remote library documentation lookup |
| **gh_grep** | Search code across open-source repos via grep.app |
| **websearch** | Exa web search, plugin-built, free tier (set `EXA_API_KEY` for higher quotas) |

**Opt-in (2 — only if you set `Z_AI_API_KEY`):**

| Server | Purpose |
|--------|---------|
| **zai_vision** | Image analysis, UI-to-code, OCR, technical diagrams, video |
| **web-search-prime** | Z.AI web search (alternative to Exa websearch) |

Both ship in the default `opencode.json` as enabled, but require `Z_AI_API_KEY` to be set in your environment (the config uses `{env:Z_AI_API_KEY}` template). Without the key, they fail silently. The agent-config `mcps` lists in `oh-my-opencode-slim.json` reference these names harmlessly regardless.

### Setting Up Z.AI

The Z.AI MCPs ship in the default config. To activate them, set `Z_AI_API_KEY` in your environment:

```bash
# Add to ~/.config/secrets/env (or ~/.profile)
export Z_AI_API_KEY="your-key-here"
source ~/.profile
```

The installer also offers to set this up during interactive install.

## Workflow Principles

See [AGENTS.md](AGENTS.md) for the complete agent rules, delegation table, pipeline workflows, and specialist instructions.

## Autonomous Mode

Want to step away and let the agent work? Use `/auto-continue on` (built into oh-my-opencode-slim).

The agent will keep working through incomplete TODOs without stopping. It stops when:
- All TODOs are completed
- It asks you a question
- You press Esc
- Max iterations reached (configurable, default 15)

**Best practice:** Write a design doc with clear TODOs before enabling. Descriptive TODOs help the agent recover context after long sessions.

**Example workflow:**
```
/remember → "Write design doc with TODOs"
/auto-continue on
# ... go make coffee, come back to finished work
```

## Directory Structure

```
~/.config/opencode/              ← occams-code (OpenCode integration layer)
├── AGENTS.md                    # OpenCode-specific agent rules and workflows
├── opencode.json                # Core config (providers, MCPs, LSPs)
├── oh-my-opencode-slim.json     # Presets, agents, fallback chains, council
├── model-profile.jsonc          # Model-mapping source of truth (regenerated into oh-my-opencode-slim.json)
├── bin/oc                       # Launcher script
├── scripts/                     # OpenCode-specific scripts
├── commands/                    # Slash command definitions
└── skills/                      # OpenCode skills (codemap, simplify, clonedeps)

~/.agents/                       ← occams-agentic (harness-agnostic framework)
├── AGENTS.md                    # Tool-agnostic workspace schema
├── repos/                       # Cloned repos, outside the wiki vault
├── scratch/                     # Ephemeral agent workspace
├── skills/                      # Universal skills (audio-analysis, video-analysis, lecture-notes, etc.)
├── scripts/                     # Universal scripts (transcribe, analyze-video.py, lecture-*.py, etc.)
└── wiki/                        # Karpathy-style LLM Wiki (Obsidian-compatible)
    ├── AGENTS.md                # Wiki schema (LLM follows these rules)
    ├── index.md                 # Master routing table
    ├── log.md                   # Append-only activity log
    ├── raw/                     # Immutable source documents
    │   ├── articles/ papers/ docs/ forums/ assets/ user/ _inbox/
    │   └── repos -> ../../repos # Symlink to cloned repos outside vault
    └── projects/ domain/ languages/ patterns/ concepts/ entities/ sources/ comparisons/
```

## License

MIT — see [LICENSE](LICENSE).
