# Wiki Log

Chronological record of all changes. Agent appends here after every wiki edit.

<!-- Entries follow this format:
## [YYYY-MM-DD] operation | Title
Notes: What changed and why
-->

## [2026-05-06] sync | Production-readiness sweep + cross-platform install hardening

### Config sync from live setup
- **opencode.json:** Anthropic adaptive thinking schema (`thinking.type:"adaptive"` + `output_config.effort`); claude-opus-4-6 → claude-opus-4-7 (3 refs); output 32K → 128K for Anthropic models. Trimmed unused: `provider.opencode.models` block (TUI metadata duplicates), `deepseek-v4-flash`, direct `deepseek-v3.2`, `openrouter/openai/gpt-5.4`. Result: 547 → 429 lines.
- **oh-my-opencode-slim.json:** Default `preset` and `council.default_preset` set to `"balanced"` (live uses `"custom"` — intentional repo difference). Premium oracle bumped to claude-opus-4-7 (temp 0.1). Council reviewers diversified across 4 distinct lineages per preset.
- **model-profile.jsonc:** Default preset = `"balanced"`. Premium orch+oracle → opus-4-7. Cleaned trailing whitespace in agent keys.

### Z.AI MCPs are now opt-in (default disabled)
- `zai_vision` and `web-search-prime` MCP blocks **removed entirely** from default `opencode.json` (they were redundant with multimodal observer + Exa websearch fallback for users without Z.AI subscription).
- The `install.sh` prompts: "Do you have a Z.AI Coding Plan subscription? [y/N]". If yes → injects the MCP blocks with the user's API key.
- agent.mcps references in slim.json kept as-is (harmless when MCPs not defined; activate automatically if user opts in later).

### Skills + scripts
- **observer.skills:** added `audio-analysis` to all 4 presets (resolves AGENTS.md inconsistency — observer is told to load /skill audio-analysis but it wasn't registered).
- **codemap SKILL.md:** path fix `~/.opencode/...` → `~/.config/opencode/...` (3 lines).
- **simplify skill:** synced from canonical 138-line version with Addy Osmani attribution.
- **NEW scripts/cleanup-logs.sh:** weekly log pruner, 30-day retention, env-overrideable. install.sh offers cron setup.

### Install.sh rewrite (cross-platform, agent-friendly)
- Detects platform (Linux/macOS/WSL) and bash version (auto-finds homebrew bash on macOS).
- **Provider questionnaire:** OpenRouter / DeepSeek / Anthropic / Z.AI / Kimi (multi-select).
- **Preset selection:** balanced / cheap / premium / custom (with hints based on selected providers).
- **Z.AI MCP prompt:** only shown if Z.AI selected. Injects MCP blocks if confirmed.
- **Transcription backend:** nix whisper.cpp / system whisper.cpp / OpenAI Whisper API / skip.
- **Optional CLIs:** defuddle (web extraction), agent-browser (browser automation).
- **Cron setup:** weekly cleanup-logs.sh.
- **PATH setup:** auto-detects shell (bash/zsh) and offers to append.
- Skill install target corrected: `~/.opencode/skills/` → `~/.config/opencode/skills/`.
- Added `model-profile.jsonc` copy step (was missing).

### Wiki updates (this commit)
- Removed stale claims about Z.AI primary web search.
- Updated observer.skills count to include audio-analysis.
- Updated config-file-locations table with current script/command counts.
- Added "Z.ai Vision MCP (Opt-in)" section with manual enable instructions.

## [2026-05-04] update | Integrate Karpathy's 4 principles into AGENTS.md

### What changed
- **@fixer: "Surgical Changes" added.** Touch only what you must. Don't "improve" adjacent code, comments, or formatting. Don't refactor things that aren't broken. Match existing style. Mention dead code — don't delete it. Clean up only orphans YOUR changes created.
- **Occam's Code: self-test heuristics added.** "Would a senior engineer say this is overcomplicated?" If yes, simplify. "Does every changed line trace to the request?" If not, revert.
- **Execution: "Think Before Coding" + verification format.** State assumptions explicitly — if multiple interpretations exist, present them rather than picking silently. Plans follow `1. [Step] → verify: [check]` — every step has a pass/fail criterion.
- From `forrestchang/andrej-karpathy-skills` — 4 principles, integrated into existing structure.

## [2026-05-03] update | Ship pipeline tools + video/audio skills + web search dual-MCP

### Shipped in this template
- **Skills:** video-analysis, audio-analysis, lecture-notes (8-phase video→Obsidian pipeline)
- **Scripts:** analyze-video.py (OpenRouter→Gemini), transcribe (whisper.cpp), lecture-scenes.py (ffmpeg scene detection), lecture-fusion.py (audio-visual fusion)
- **Web search:** dual MCP — `websearch` (Exa, default, plugin-built) + `web-search-prime` (Z.AI, opt-in for subscribers). Both assigned to orchestrator, oracle, designer, librarian in all presets. Explorer, fixer, observer excluded.
- **Wiki pages:** occams-code-setup, agent-roles-and-models, vision-integration updated with full tool/skill/MCP tables

## [2026-04-10] init | Wiki initialized

Notes: Occams-code wiki scaffold created from template.
