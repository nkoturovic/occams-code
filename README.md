# Occam's Code

> OpenCode setup sharpened by Occam's Razor.
> *The simplest solution that fully solves the problem is the correct solution.*

A shareable, open-source configuration for [OpenCode](https://github.com/sst/opencode) — an AI coding agent with multi-model orchestration, Karpathy-style persistent wiki memory, and a smart launcher.

**The default `balanced` preset works fully with just an OpenRouter API key.** Other presets unlock additional capabilities if you have Anthropic / DeepSeek / Z.AI / Kimi keys, but you don't need them to start.

```bash
git clone https://github.com/nkoturovic/occams-code.git && cd occams-code
./scripts/install.sh                                    # interactive
```

## What's Included

- **`oc` launcher** (`bin/oc`) — Interactive preset picker, project initialization, health checks, and permission toggles
- **5 presets** — `balanced` (default, OpenRouter-only), `cheap`, `deepseek`, `premium`, `custom`
- **10 Python scripts** + `transcribe` + `cleanup-logs.sh` — Config generator, wiki lint, project init, repo ingestion, project state detection, model health check, video analysis, lecture scene detection, lecture audio-visual fusion, lecture clip encoding, speech-to-text, weekly log pruner
- **6 slash commands** — `/preset`, `/wiki`, `/remember`, `/permissions`, `/wiki-lint`, `/model-switch` (plus `/auto-continue` from oh-my-opencode-slim)
- **oh-my-opencode-slim** plugin — 7 agent roles with curated models, fallback chains, and council multi-LLM consensus
- **model-profile.jsonc** — Single source of truth for model assignments. Edit, run `oc --sync-profile`, restart. Plus per-project overrides via `.opencode/oh-my-opencode-slim.jsonc`
- **4 MCP servers** — context7 (library docs) + grep_app (code search) + zai_vision (image analysis) + web-search-prime (Z.AI web search). All ship in the default config; zai_vision and web-search-prime require a Z.AI API key set via `Z_AI_API_KEY` env var.
- **6 local OpenCode skills** — audio-analysis, video-analysis, lecture-notes, codemap, simplify, clonedeps (plus 5 from the obsidian-skills bundle if cloned: defuddle, json-canvas, obsidian-bases, obsidian-cli, obsidian-markdown)
- **Karpathy-style wiki** — Persistent knowledge base (raw → wiki one-way compile), Obsidian-compatible
- **AGENTS.md + AGENTS-system.md** — OpenCode-specific agent rules plus a tool-agnostic `~/.agents/` workspace schema

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
```

The installer:
1. Copies scripts, commands, configs, AGENTS.md to `~/.config/opencode/`
2. Sets up the unified agent workspace at `~/.agents/` (wiki, repos, scratch, skills)
3. Installs the oh-my-opencode-slim plugin
4. Optionally installs Obsidian

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
oc --preset <name>  Set preset, create project config, launch
oc --doctor         Run diagnostics (config, wiki, lint)
oc --sync-profile    Regenerate config from model-profile.jsonc
oc --init-project   Create project wiki page + AGENTS.md + project .agents workspace
oc --ingest-repo URL  Snapshot GitHub repo into wiki
oc -c               Continue last session
```

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

| Preset | Use case | Required keys | Notes |
|--------|----------|---------------|-------|
| `balanced` | **Default** — daily development | OpenRouter only | GLM-5.1 oracle, DeepSeek V3.2 explorer/fixer, Qwen 3.6 Plus librarian/council, Gemini Flash designer/observer |
| `cheap` | Exploration, bulk tasks | OpenRouter only | Free Nemotron for explorer/librarian; Qwen3-Coder orchestrator; Qwen 3.6 Plus oracle |
| `deepseek` | DeepSeek-heavy reasoning | DeepSeek API + OpenRouter | DeepSeek V4 Pro for all reasoning roles; Gemini Pro for designer/observer |
| `premium` | Complex architecture, debugging | OpenRouter + Anthropic | Claude Opus 4.7 (orchestrator, oracle, council), Claude Sonnet 4.6 (explorer, librarian, fixer), Gemini Pro (designer, observer) |
| `custom` | Subscription-based | Z.AI + Kimi + DeepSeek + OpenRouter | Z.AI GLM-5.1 (orchestrator, oracle, explorer, librarian), Kimi for Coding (fixer), DeepSeek V4 Pro (council), Gemini Pro (designer, observer) |

**The default `balanced` preset works fully with just an OpenRouter key.** The other presets require additional API keys/subscriptions.

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
- Never set `presets` in a project config — it wipes out all global preset definitions

The plugin deep-merges project config with global config. Edit the file directly — no wizard needed. `.opencode/` is gitignored.

### Continuing Old Sessions After Config Changes

> ⚠️ When you continue an old session (via startup prompt or `/sessions`), OpenCode restores the model from the session's **last user message**, overriding your current config. Subagents are unaffected — they always use the current config.

**Workaround:** After continuing an old session, use `/models` to select the correct model. Temperature and options are always from the current config — only the model ID needs fixing. Alternatively, start a new session instead.

### Scripts

| Script | Purpose |
|--------|---------|
| `model-profile.py` | **Config generator** — generates oh-my-opencode-slim.json from model-profile.jsonc |
| `wiki-lint.py` | Wiki health check (dead links, orphans, stale pages) |
| `project-init.py` | Creates global project wiki page + project-root AGENTS.md + project `.agents/` workspace |
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
├── AGENTS.md                      # OpenCode-specific agent rules and workflows
├── opencode.json                  # Core config (providers, MCPs, LSPs)
├── oh-my-opencode-slim.json       # Presets, agents, fallback chains, council
├── model-profile.jsonc            # Source-of-truth for model assignments (oc --sync-profile regenerates slim.json)
├── bin/oc                         # Launcher script
├── scripts/                       # 10 Python scripts + transcribe + cleanup-logs.sh
├── commands/                      # Slash command definitions (6 commands)
├── skills/                        # OpenCode skills (codemap, simplify, clonedeps, audio/video/lecture pipeline)

~/.agents/
├── AGENTS.md                      # Tool-agnostic workspace schema
├── repos/                         # Cloned repos, outside the wiki vault
├── scratch/                       # Ephemeral agent workspace
├── skills/                        # Tool-agnostic ecosystem skills
└── wiki/
    ├── AGENTS.md                  # Wiki schema (LLM follows these rules)
    ├── index.md                   # Master routing table
    ├── log.md                     # Append-only activity log
    ├── overview.md                # High-level wiki synthesis
    ├── raw/                       # Immutable source documents
    │   ├── articles/ papers/ docs/ forums/ assets/ user/ session-reports/ _inbox/
    │   └── repos -> ../../repos   # Symlink to cloned repos outside vault
    └── projects/ domain/ languages/ patterns/ concepts/ entities/ sources/ comparisons/
```

## License

MIT — see [LICENSE](LICENSE).
