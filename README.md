# Occam's Code

> OpenCode setup sharpened by Occam's Razor.
> *The simplest solution that fully solves the problem is the correct solution.*

A shareable, open-source configuration for [OpenCode](https://github.com/sst/opencode) — an AI coding agent with multi-model orchestration, Karpathy-style persistent wiki memory, and a smart launcher.

**The default `balanced` preset works fully with just an OpenRouter API key.** Other presets unlock additional capabilities if you have Anthropic / DeepSeek / Z.AI / Kimi keys, but you don't need them to start.

```bash
git clone https://github.com/nkoturovic/occams-code.git && cd occams-code
./scripts/install.sh                                    # interactive
# OR for AI agents / CI:
OCCAM_PROVIDERS=openrouter ./scripts/install.sh --unattended
```

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, project initialization, health checks, and permission toggles
- **4 presets** — `balanced` (default), `cheap`, `premium`, `custom`
- **8 Python scripts** + `transcribe` + `cleanup-logs.sh` — Config generator, wiki lint, project init, repo ingestion, project state detection, video analysis, lecture scene detection, lecture audio-visual fusion, speech-to-text, weekly log pruner
- **6 slash commands** — `/preset`, `/wiki`, `/remember`, `/permissions`, `/wiki-lint`, `/model-switch` (plus `/auto-continue` from oh-my-opencode-slim)
- **oh-my-opencode-slim** plugin — 7 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **model-profile.jsonc** — Single source of truth for model assignments. Edit, run `oc --sync-profile`, restart. Plus per-project overrides via `.opencode/oh-my-opencode-slim.jsonc`
- **3 default MCPs + 2 opt-in** — context7 (library docs) + grep_app (code search) + websearch (Exa, free tier) ship by default; zai_vision + web-search-prime are injected by the installer only if you have a Z.AI subscription
- **5 local skills** — audio-analysis, video-analysis, lecture-notes, codemap, simplify (plus 5 from the obsidian-skills bundle if cloned: defuddle, json-canvas, obsidian-bases, obsidian-cli, obsidian-markdown)
- **Karpathy-style wiki** — Persistent knowledge base (raw → wiki one-way compile), Obsidian-compatible
- **AGENTS.md** — 7 agent roles with specialist instructions, pipeline workflows, and multi-agent delegation rules

## Quick Start

### Prerequisites

- [OpenCode](https://github.com/sst/opencode) (`npm install -g opencode` or `bun install -g opencode`)
- Python 3.10+, Bash 4.0+, [jq](https://stedolan.github.io/jq/), git, curl
- `npm` or `bun` (for installing the oh-my-opencode-slim plugin)
- An API key for at least one provider (**OpenRouter recommended for the OOB `balanced` preset**)

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
# or unattended (e.g. for AI agents / CI):
OCCAM_PROVIDERS=openrouter ./scripts/install.sh --unattended
```

The installer:
1. Asks 6 questions (providers, default preset, Z.AI opt-in, transcription backend, optional CLIs, cron + PATH)
2. Copies scripts, commands, configs, AGENTS.md to `~/.config/opencode/`
3. Sets up the wiki template at `~/wiki/`
4. Installs the oh-my-opencode-slim plugin
5. Optionally injects Z.AI MCP blocks if you confirmed a Z.AI subscription

Set up your API keys — the installer's **step 7** writes them to `~/.config/secrets/env` (sourced by `~/.profile`) and optionally to OpenCode's `~/.local/share/opencode/auth.json`. Both stores serve different consumers:
- `~/.config/secrets/env` — env vars read by scripts (`analyze-video.py`, `transcribe`) and MCPs (`websearch` Exa, `zai_vision`)
- `~/.local/share/opencode/auth.json` — JSON keys read by OpenCode core for provider routing

See [INSTALL.md](INSTALL.md) for the full env-var reference (`OCCAM_*`), CLI flags, manual install, and per-platform instructions.

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
oc --preset <name>  Set preset, create project config, launch
oc --doctor         Run diagnostics (config, wiki, lint)
oc --sync-profile    Regenerate config from model-profile.jsonc
oc --init-project   Create project wiki page + AGENTS.md
oc --ingest-repo URL  Snapshot GitHub repo into wiki
oc -c               Continue last session
```

### Permissions

By default `opencode.json` ships with `"permission": "allow"` — the agent auto-approves every tool call. This is good for trusted local work; not great for code you didn't write yourself.

- `oc --safe` — temporarily switches to permission prompts for the current session (restored on exit).
- To make prompts the persistent default, remove `"permission": "allow"` from `~/.config/opencode/opencode.json`. Then use `oc --unsafe` for one-off auto-approve sessions.

### The Wiki

The wiki at `~/wiki/` follows Karpathy's LLM Wiki pattern:

- **`raw/`** — Immutable source documents (articles, repos, papers). Never modify.
- **`wiki/`** — LLM-generated knowledge base (summaries, concepts, patterns, project pages)
- **`AGENTS.md`** — Schema that tells the LLM how to maintain the wiki

Open `~/wiki/` in [Obsidian](https://obsidian.md) for the best experience. The LLM maintains all content — you provide sources and curate.

### Presets

| Preset | Use case | Required keys | Notes |
|--------|----------|---------------|-------|
| `balanced` | **Default** — daily development | OpenRouter only | OOB-usable: all primary models route through OpenRouter (GLM, Qwen, DeepSeek V3.2, Gemini Flash, Kimi K2.6) |
| `cheap` | Exploration, bulk tasks | OpenRouter only | Free Nemotron for explorer/librarian; paid Qwen Coder for orchestrator; mixed paid/free elsewhere |
| `premium` | Complex architecture, debugging | OpenRouter + Anthropic | Claude Opus 4.7 (orchestrator, oracle), Claude Sonnet 4.6 (explorer, librarian, fixer), Gemini 3.1 Pro (designer), Kimi K2.6 (observer) |
| `custom` | Subscription-based | DeepSeek + Kimi + Z.AI | DeepSeek V4 Pro (orchestrator, oracle) + Kimi for Coding ($39/mo, 4 agents) + Z.AI GLM-5.1 ($30/mo, 2 agents) |

**The default `balanced` preset works fully with just an OpenRouter key.** The other presets require additional API keys/subscriptions.

### Per-Project Config

The `oc` launcher creates `.opencode/oh-my-opencode-slim.jsonc` (preferred, supports comments) or `.json` in your project root on first run. Override preset or individual agent models:

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
| `model-profile.py` | **Config generator** — generates oh-my-opencode-slim.json from model-profile.jsonc |
| `wiki-lint.py` | Wiki health check (dead links, orphans, stale pages) |
| `project-init.py` | Creates wiki page + project AGENTS.md |
| `repo-ingest.py` | Snapshots GitHub repo into wiki |
| `detect-project-state.py` | Project state detection (used by --doctor) |
| `analyze-video.py` | Video analysis via OpenRouter (Gemini, multi-provider) |
| `lecture-scenes.py` | Scene detection + keyframe extraction (ffmpeg) |
| `lecture-fusion.py` | Audio-visual fusion for lecture notes pipeline |
| `transcribe` | Speech-to-text. Default backend: whisper.cpp via nix flake (Linux/WSL, Vulkan GPU). Installer offers system whisper-cpp / OpenAI API as alternatives |
| `cleanup-logs.sh` | Weekly log pruner (30-day retention, runs via cron if installer set it up) |

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
| **grep_app** | Search code across open-source repos |
| **websearch** | Exa web search, plugin-built, free tier (set `EXA_API_KEY` for higher quotas) |

**Opt-in (2 — only if you have a Z.AI subscription, installer prompts for the key):**

| Server | Purpose |
|--------|---------|
| **zai_vision** | Image analysis, UI-to-code, OCR, technical diagrams, video |
| **web-search-prime** | Z.AI web search (alternative to Exa websearch) |

The default repo config does **not** ship Z.AI MCP blocks. The installer asks "Do you have a Z.AI subscription?" — if yes, it injects the blocks via `jq` with your API key. If no, the agent.mcps lists in `oh-my-opencode-slim.json` reference these names harmlessly (they're no-ops without the MCPs declared).

### Adding Z.AI Later

If you skipped Z.AI during install and want to enable it later, see [INSTALL.md → Z.AI MCPs (Opt-in)](INSTALL.md#zai-mcps-opt-in) for the `jq` snippet that injects the blocks.

## Workflow Principles

See [AGENTS.md](AGENTS.md) for the complete agent rules, delegation table, pipeline workflows, and specialist instructions.

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
├── opencode.json                  # Core config (providers, MCPs, LSPs)
├── oh-my-opencode-slim.json       # Presets, agents, fallback chains, council
├── model-profile.jsonc            # Source-of-truth for model assignments (oc --sync-profile regenerates slim.json)
├── bin/oc                         # Launcher script
├── scripts/                       # 8 Python scripts + transcribe + cleanup-logs.sh
├── commands/                      # Slash command definitions (6 commands)
├── skills/                        # Local skills (codemap, simplify, audio/video/lecture pipeline)

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
