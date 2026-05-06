# Occam's Code

> OpenCode setup sharpened by Occam's Razor.

> The simplest solution that fully solves the problem is the correct solution.

A shareable, open-source configuration for [OpenCode](https://github.com/sst/opencode) — an AI coding agent with multi-model orchestration, Karpathy-style persistent wiki memory, and a smart launcher.

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, project initialization, health checks, and permission toggles
- **4 presets** — `balanced` (default), `cheap`, `premium`, `custom` (subscription-based)
- **8 Python scripts + transcribe** — Config generator, wiki lint, project init, repo ingestion, project state detection, video analysis, lecture scene detection, lecture audio-visual fusion, local speech-to-text (whisper.cpp)
- **6 slash commands** — `/preset`, `/wiki`, `/remember`, `/permissions`, `/wiki-lint`, `/model-switch` (plus `/auto-continue` from oh-my-opencode-slim)
- **oh-my-opencode-slim** config — 7 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **model-profile.jsonc** — Single source of truth for model assignments. Edit this file, run `oc --sync-profile`, restart. Plus per-project overrides via `.opencode/oh-my-opencode-slim.jsonc`
- **4 MCP servers** — context7 (library docs), grep_app (code search), zai_vision (image analysis, opt-in), web-search-prime (Z.AI, opt-in)
- **Plugin-built websearch** — Exa fallback (free tier, higher quotas with `EXA_API_KEY`)
- **5 local skills** — audio-analysis, video-analysis, lecture-notes, codemap, simplify (plus 5 from obsidian-skills plugin if installed: defuddle, json-canvas, obsidian-bases, obsidian-cli, obsidian-markdown)
- **Karpathy-style wiki** — Persistent knowledge base (raw → wiki one-way compile), Obsidian-compatible
- **AGENTS.md** — 7 agent roles with specialist instructions, pipeline workflows, and multi-agent delegation rules

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
oc --sync-profile   # Regenerate oh-my-opencode-slim.json from model-profile.jsonc
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

Default is `--unsafe` (auto-approve). We trust you. You trust your agents. Life's too short for permission dialogs.

To make prompts the default, remove `"permission": "allow"` from `~/.config/opencode/opencode.json`. Then use `oc --unsafe` when you want to live dangerously.

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
| `cheap` | Exploration, bulk tasks | OpenRouter only | Heavy use of free tier (Nemotron, Qwen Coder Free) |
| `premium` | Complex architecture, debugging | OpenRouter + Anthropic | Claude Opus 4.7 (orchestrator + oracle), Sonnet 4.6 (workers), Gemini Pro (designer) |
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

Default (always enabled):

| Server | Purpose |
|--------|---------|
| **context7** | Remote library documentation lookup |
| **grep_app** | Search code across open-source repos |
| **websearch** | Exa web search (plugin-built, free tier; `EXA_API_KEY` for higher quotas) |

Opt-in (only if you have a Z.AI subscription — installer prompts for the key):

| Server | Purpose |
|--------|---------|
| **zai_vision** | Image analysis, UI-to-code, OCR, technical diagrams, video |
| **web-search-prime** | Z.AI primary web search alternative to Exa |

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
├── scripts/                       # 9 Python scripts + transcribe + cleanup-logs.sh
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
