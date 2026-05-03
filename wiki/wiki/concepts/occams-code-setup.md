---
summary: "Occam's Code architecture: two-config system, presets, agents, fallback, council, skills, and scripts"
type: concept
tags: [occams-code, opencode, architecture, setup]
sources: []
related:
  - agent-roles-and-models
  - oc-launcher
  - troubleshooting
created: 2026-04-10
updated: 2026-04-23
confidence: high
---

# Occam's Code Setup Architecture

## Two-Config System

Occam's Code uses two config files with separate responsibilities:

| File | Purpose | Edit manually? |
|------|---------|----------------|
| `opencode.json` | Core: providers, model definitions, MCP servers, LSP config, permissions | Rarely (permissions only) |
| `oh-my-opencode-slim.json` | Plugin: presets, agent models, fallback chains, council, continuation | Yes — via `oc` or direct edit |

**Key relationship:** A model in `oh-my-opencode-slim.json` must have a corresponding provider entry in `opencode.json`. If OpenCode can't find the model in any provider, the call fails.


## Presets

Four presets, ordered by cost:

| Preset | Use case | Key models |
|--------|----------|------------|
| **cheap** | Exploration, bulk tasks | Qwen Coder, DeepSeek, Nemotron (free), Gemini Flash |
| **balanced** | Default — best cost/quality trade-off | GLM-5.1, Claude Sonnet, DeepSeek, Qwen, Gemini Flash |
| **premium** | Critical work — best available | Claude Opus, Claude Sonnet, Gemini Pro |
| **custom** | Subscription-based — mirrors live setup's Kimi+GLM allocation | Kimi K2.6 (4 agents), GLM-5.1 (3 agents) |

Active preset is set in `oh-my-opencode-slim.json` → `"preset"` field.

## Agent Configuration Shape

Each agent in a preset has:

```json
{
  "model": "provider/model-name",
  "variant": "high",       // "low", "medium", "high", "max" — inference effort
  "temperature": 0.3,      // 0-2, controls randomness
  "skills": ["*"],         // Skill names or "*" for all
  "mcps": ["websearch"]    // MCP server names the agent can use
}
```

**Variant** controls how much compute the model uses. `"high"` is the default for most roles. `"max"` is reserved for premium orchestrator/oracle where maximum reasoning depth matters.

## Fallback Chains

Every agent has a fallback chain (5 models, ordered by quality):

```json
"fallback": {
  "enabled": true,
  "timeoutMs": 60000,
  "chains": {
    "orchestrator": ["best-model", "second-best", "...", "free-safety-net"],
    "...": ["..."]
  }
}
```

- **Sequential, not random:** models tried in array order
- **Timeout-triggered:** if primary doesn't respond in 60s, next model is tried
- **Quality gradient:** each chain goes best → good → acceptable → cheap → free
- **Free safety net:** last entry is always a free model (zero cost, limited capability)

## Council (Multi-LLM Consensus)

Council sends a question to multiple models in parallel, then a master synthesizes their responses:

```json
"council": {
  "master": { "model": "provider/model" },
  "default_preset": "balanced",
  "councillor_execution_mode": "parallel",
  "presets": {
    "balanced": {
      "master": { "model": "..." },
      "reviewer-1": { "model": "..." },
      "reviewer-2": { "model": "..." },
      "reviewer-3": { "model": "..." }
    }
  }
}
```

- **4 distinct models per session** — master + 3 reviewers from different providers/training lineages
- **Master ≠ any reviewer** — avoids bias from seeing its own output
- **No duplicate reviewers** — each reviewer brings a unique perspective
- **Per-preset overrides:** each preset can override the global master model

## Todo Continuation (Auto-Continue)

Built into oh-my-opencode-slim. Config:

```json
"todoContinuation": {
  "maxContinuations": 50,      // Hard cap (plugin zod schema: .max(50))
  "cooldownMs": 5000,          // 5s pause between iterations (cancel window)
  "autoEnable": false,         // Must toggle via /auto-continue on
  "autoEnableThreshold": 4     // Only triggers when ≥4 TODOs exist
}
```

- **On-demand only:** `autoEnable: false` — user activates per-session via `/auto-continue on`
- **Stops when:** all TODOs complete, agent asks question, user presses Esc, max iterations reached
- **Best practice:** write a design doc with descriptive TODOs before enabling

## Skills

Skills are **on-demand procedural expertise** for agents. They differ from AGENTS.md (always loaded) and MCP tools (live connections).

### Bundled with OpenCode (no installation needed)
- **agent-browser** — Browser automation, screenshots, web scraping
- **code-review** — Structured code review, security audit
- **simplify** — Code cleanup after writing
- **pr-integration** — GitHub PR create/review

### Bundled with occams-code
- **video-analysis** — Video understanding via OpenRouter→Gemini (observer)
- **audio-analysis** — Speech-to-text via whisper.cpp local (observer, reference only)
- **lecture-notes** — 8-phase pipeline: lecture video → structured Obsidian note (orchestrator + observer)

### From obsidian-skills repo (installed by `install.sh`)
- **defuddle** — Clean markdown from web pages
- **obsidian-cli** — Obsidian CLI interaction
- **obsidian-markdown** — Wikilinks, callouts, frontmatter, embeds
- **obsidian-bases** — Obsidian Bases (.base files)
- **json-canvas** — JSON Canvas files (.canvas)

### Per-agent skill assignments
- **orchestrator:** `"*"` (all skills)
- **designer:** `["agent-browser"]` (needs browser for visual verification)
- **observer (all presets):** `["video-analysis", "lecture-notes"]` (vision + pipeline awareness)
- **all others:** `[]` (no skills — they operate through tools and MCPs)

## Scripts

All scripts live in `~/.config/opencode/scripts/`:

| Script | What it does |
|--------|-------------|
| `detect-project-state.py` | Outputs shell vars for wiki/memory state (HAS_WIKI_PAGE, WIKI_STALE, etc.) |
| `project-init.py` | Creates wiki page + project AGENTS.md |
| `repo-ingest.py` | Snapshots GitHub repo into wiki raw/repos/ with code insights |
| `wiki-lint.py` | Checks dead links, orphans, stale pages, missing frontmatter. `--json` |
| `model-profile.py` | **Config generator** — reads `model-profile.jsonc`, generates full `oh-my-opencode-slim.json` |
| `analyze-video.py` | Video analysis via OpenRouter→Gemini (audio+visual, ≤20MB) |
| `transcribe` | Local speech-to-text via whisper.cpp Vulkan GPU (Serbian/English) |
| `lecture-scenes.py` | Lecture scene detection + keyframe extraction → scenes.json |
| `lecture-fusion.py` | Fuse transcript sections + video scenes → segments.json (per-section frames) |

## Permissions

- **`--unsafe`** (default): sets `"permission": "allow"` in opencode.json — auto-approve all
- **`--safe`**: removes the permission key — OpenCode prompts for every tool use
- **Implementation:** `bin/oc` backs up current state to temp file, modifies config, uses shell `trap` to restore on exit
- **Mutually exclusive:** specifying both `--safe` and `--unsafe` exits with error
- **Edge case:** if OpenCode crashes hard (SIGKILL), the trap may not fire — check `opencode.json` manually if permissions seem stuck

## Related
- [[agent-roles-and-models]] — Per-agent design rationale and delegation strategy
- [[oc-launcher]] — Boot sequence, session modes, sync profiles
- [[troubleshooting]] — Common failure modes and diagnostic commands
