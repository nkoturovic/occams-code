# Wiki Log

Chronological record of all changes. Agent appends here after every wiki edit.

<!-- Entries follow this format:
## [YYYY-MM-DD] operation | Title
Notes: What changed and why
-->

## [2026-05-03] update | Ship pipeline tools + video/audio skills + web search fallback

### Shipped in this template
- **Skills:** video-analysis, audio-analysis, lecture-notes (8-phase video→Obsidian pipeline)
- **Scripts:** analyze-video.py (OpenRouter→Gemini), transcribe (whisper.cpp), lecture-scenes.py (ffmpeg scene detection), lecture-fusion.py (audio-visual fusion)
- **Web search:** dual MCP — `web-search-prime` (Z.AI, primary) + `websearch` (Exa, fallback, plugin-built). Both assigned to orchestrator, oracle, designer, librarian in all presets. Explorer, fixer, observer excluded.
- **Observer skills:** `["video-analysis", "lecture-notes"]` in all presets for vision + pipeline awareness
- **Wiki pages:** occams-code-setup, agent-roles-and-models, vision-integration updated with full tool/skill/MCP tables

## [2026-04-10] init | Wiki initialized
Notes: Occams-code wiki scaffold created from template.

## [2026-05-04] update | Integrate Karpathy's 4 principles into AGENTS.md

### What changed
- **@fixer: "Surgical Changes" added.** Touch only what you must. Don't "improve" adjacent code, comments, or formatting. Don't refactor things that aren't broken. Match existing style. Mention dead code — don't delete it. Clean up only orphans YOUR changes created.
- **Occam's Code: self-test heuristics added.** "Would a senior engineer say this is overcomplicated?" If yes, simplify. "Does every changed line trace to the request?" If not, revert.
- **Execution: "Think Before Coding" + verification format.** State assumptions explicitly — if multiple interpretations exist, present them rather than picking silently. Plans follow `1. [Step] → verify: [check]` — every step has a pass/fail criterion.
- From `forrestchang/andrej-karpathy-skills` — 4 principles, integrated into existing structure.
