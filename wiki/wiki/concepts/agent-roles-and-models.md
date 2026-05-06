---
summary: "Per-agent design rationale, delegation strategy, model selection criteria, and MCP allocation"
type: concept
tags: [occams-code, opencode, agents, models, delegation]
sources: []
related:
  - model-profile-guide
  - subscription-scenarios
created: 2026-04-10
updated: 2026-05-03
confidence: high
---

# Agent Roles and Model Selection

## The 8 Roles

| Role | Purpose | Call frequency | Cost sensitivity |
|------|---------|---------------|-----------------|
| **Orchestrator** | Master delegator, strategic coordinator | Every message | Low — best available justified |
| **Oracle** | Deep reasoning, architecture, code review | Infrequent, high-stakes | Low — quality over cost |
| **Observer** | Read-only visual analysis: images, PDFs, video | Moderate | Medium — needs multimodal |
| **Designer** | UI/UX, visual polish, responsive layouts | Moderate | Medium — creative reasoning |
| **Explorer** | Fast parallel codebase search | High (3+ parallel calls) | High — cost × parallelism |
| **Librarian** | Documentation lookup, API references | Moderate | High — broad knowledge > depth |
| **Fixer** | Fast bounded implementation (<20 lines) | High | High — speed matters |
| **Council** | Multi-LLM consensus (master + 3 reviewers) | Rare, critical decisions | Low — diversity justifies cost |

## Delegation Strategy

**Delegate when:**
- Discovering what exists → `@explorer` (parallel search)
- Implementation work → `@fixer` (bounded execution)
- Library docs/API refs → `@librarian` (external knowledge)
- Architecture decisions → `@oracle` (deep reasoning)
- Visual analysis (images, PDFs, video) → `@observer` (fact extraction)
- UI/UX polish → `@designer` (creative intent, often after @observer)
- Critical decisions → `@council` (multi-perspective)

**Don't delegate when:**
- Single small change (<20 lines, one file)
- You already have the file in context
- Explaining takes longer than doing

## Model Selection Criteria Per Role

### Orchestrator — Best reasoning + instruction following
Needs: complex delegation decisions, multi-step planning, understanding when to delegate vs do it yourself. Top-tier reasoning is non-negotiable.
- Best: DeepSeek V4 Pro (1M context, hybrid reasoning), Claude Sonnet 4, GLM-5.1
- Acceptable: Qwen 3.6 Plus, DeepSeek V3.2
- **Orchestrator chain has free tail** (6 positions total — quality gradient down to free safety net)

### Oracle — Strongest reasoning, lowest hallucination
Needs: architecture decisions, complex debugging, code review. Infrequent but high-stakes — quality justifies cost.
- Best: DeepSeek V4 Pro (1M context, hybrid reasoning), Claude Opus 4, Claude Sonnet 4, Gemini 3.1 Pro
- Acceptable: GLM-5.1 (strong reasoning, open-source)

### Observer — Vision + audio analysis
Needs: accurate image/PDF/video/audio reading, structured text output, low variance. Must support vision (Kimi) and has bash access for audio scripts (whisper.cpp).
- Best: Kimi K2.6 (262K context, native image + video via `video_url` keyframe extraction), Gemini 3.1 Pro
- Acceptable: Gemini 3 Flash (cheap preset), Claude Sonnet 4 (fallback)
- Temperature: 0.1 (deterministic — same image should yield same observation)
- **Tools:** Read (images/PDFs), `zai_vision` MCP (fallback), `analyze-video.py` (video), `transcribe` (audio via whisper.cpp local)
- **Video support:** `analyze-video.py` script — Kimi K2.6 (visual keyframes, 100MB) or OpenRouter→Gemini (audio+visual, 20MB). MCP `video_analysis` (≤8MB) as fallback.
- **Audio support:** `transcribe` script — whisper.cpp Vulkan GPU, local. Auto-extracts audio from video, outputs SRT with timestamps.
- **Combined:** For lectures/talks, run transcribe + analyze-video in parallel, merge by timestamp.
- **Skills:** `video-analysis`, `audio-analysis` (auto-discovered, loaded on demand)
- **Observer chain includes GLM-5V-Turbo** as cross-provider vision fallback + free tail (7 positions total)

### Designer — Multimodal capability + creativity
Needs: screenshot analysis, CSS/layout reasoning, responsive design, accessibility. Must support vision input.
- Default (live): Kimi for Coding K2.6 (via Kimi Coding Plan) — best Visual QA, native multimodal, follows Read-first instructions
- Repo presets: Gemini 3 Flash (cheap/balanced), Gemini 3.1 Pro (premium)
- Fallback (live): Kimi-for-coding → Kimi K2.6 (OR) → Gemini 3.1 Pro → Gemini Flash → Claude Sonnet 4.6 → Qwen3 Coder Free
- Fallback (repo): Gemini 3.1 Pro → Gemini Flash → Claude Sonnet 4.6 → Qwen3 Coder Free
- Temperature: 0.5 (higher than other roles — creative exploration)
- Tools: agent-browser, context7, web-search-prime (Z.AI), websearch (Exa fallback). `zai_vision` MCP on all presets for designer; observer has it in all presets.
- Note: Flash and K2.6 grabbed MCP instead of Read. Only Pro follows Read-first. zai_vision excluded from Flash presets architecturally.

### Explorer — Speed + cost efficiency
Needs: fast parallel grep/AST queries, summarize results. Runs 3+ calls concurrently — cost compounds.
- Best: DeepSeek V3.2 (cheap, fast, good at code comprehension), Qwen 3.6 Plus
- Free acceptable: Nemotron (for cheap preset)

### Librarian — Broad knowledge + speed
Needs: doc synthesis across libraries, API reference lookup. Breadth of knowledge matters more than depth.
- Best: Qwen 3.6 Plus (broad training, fast), DeepSeek V3.2
- Free acceptable: Nemotron (for cheap preset)

### Fixer — Coding ability + tool use reliability
Needs: precise code edits, bounded implementation, follows specifications exactly. Must be different training lineage from orchestrator for delegation diversity.
- Best: DeepSeek V3.2 (excellent coding, cheap), GLM-5.1, Claude Sonnet 4
- Key: **fixer should differ from orchestrator** — same model brings no new perspective when delegated to

## Temperature Strategy

Temperatures are set **per model** following vendor defaults and coding-specific guidance, not per role. Role-based temperatures are a starting point, but vendor mandates override them.

### Vendor Defaults and Coding Recommendations

| Model | Vendor Default | Coding/Agentic Rec | Our Setting | Why |
|-------|---------------|-------------------|-------------|-----|
| **GLM-5.1** | 1.0 | 1.0 (coding benchmarks) | **0.4–0.6 per-agent** | Vendor default 1.0 works for benchmarks, but per-agent tuning improves agentic tasks: oracle 0.5 (precision), explorer 0.3 (consistency), librarian 0.6 (synthesis), orchestrator 0.6 (balanced). Council diversity reviewers stay at 1.0. |
| **Kimi K2.6** | API-enforced¹ | API-enforced¹ | **0.1–0.7 explicit** | Temperature set explicitly for all Kimi agents (designer 0.7, fixer 0.1, observer: now uses Gemini). API tolerates temperature alongside thinking mode. Thinking budget: 32000 (max). |
| **Claude Sonnet/Opus 4.6** | 1.0 | ~0.0 (analytical) | **0.1-0.3** | Low temps align with vendor "analytical" guidance. No specific agentic recommendation found. |
| **DeepSeek V3.2** | 1.0 | 0.0 (pure coding), 0.2-0.4 (exploratory) | **0.1-0.2** | Conservative for agentic tool-calling. No thinking mode — reliable multi-turn. |
| **DeepSeek V4 Pro** | 1.0 (thinking ignores) | 1.0 (thinking ignores) | **0.1–0.3 explicit** | API ignores temperature in thinking mode (tested: identical output at None/0.0/1.0). Set explicitly for consistency: orchestrator 0.3, oracle 0.1. Previously broken for multi-turn; **fixed** via `@ai-sdk/deepseek@2.0.30` (2026-04-29). Now stable for orchestrator + oracle with full tool-call support. **Switched to @ai-sdk/openai-compatible** (2026-05-06) for explicit `reasoning_effort` support. |
| **Gemini 3.x** | **1.0** | **1.0 strongly recommended** | **1.0** | Google: "strongly recommend keeping temperature at 1.0. Setting below 1.0 may lead to looping or degraded performance." |
| **Nemotron 3 Super** | **1.0** | **1.0 across ALL tasks** | **1.0** | NVIDIA: "temperature=1.0 across all tasks and serving backends — reasoning, tool calling, and general chat alike." |
| **Qwen 3.6 Plus** | 0.65 | 0.6 (thinking mode, precise coding) | **0.6** | Unsloth/Qwen: 0.6 for precise coding in thinking mode. |
| **Qwen 3 Coder** | 0.65 | 1.0 (across all backends) | **1.0** | Qwen team recommends 1.0 for Coder models universally. |

¹ **Kimi for Coding API**: Temperature is set explicitly on all Kimi agents (0.1–0.7) alongside thinking mode (budget 32000). Previously believed that API rejected wrong temps — confirmed incorrect. Temperature is tolerated alongside thinking. |

### Key Principle

**Follow vendor defaults unless there's a specific coding recommendation.** The "lower is better for coding" heuristic is wrong for modern reasoning models (Gemini 3, Nemotron) and can cause active harm (looping, degraded performance). For GLM-5.1 specifically, vendor default 1.0 works for benchmarks but per-agent tuning (0.4–0.6) produces better agentic results. Only override when:
1. Vendor explicitly recommends a different value for coding
2. The model is non-reasoning and used for deterministic tasks (DeepSeek V3.2 at 0.1-0.2)
3. The API enforces its own value (Kimi)

### Two Kinds of "Looping"

Vendor warnings about temperature < 1.0 causing "looping" refer to **token repetition** — the model gets stuck generating the same characters/phrase verbatim (e.g., `"Wait wait wait..."`, repeated `\n`). Fix: raise temp toward 1.0.

The behavior that prompted our GLM tuning was different — **verbose hedging** — where the model generates different words but makes no progress ("Hmm", "Actually", "But on the other hand"). Fix: lower temp to reduce hedging token probability.

These have opposite fixes. Diagnose which one you're seeing before adjusting temperature. (Ref: arxiv 2512.12895 — "Wait, Wait, Wait... Why Do Reasoning Models Loop?")

### Temperature Audit Log

- **2026-04-24**: Full audit of all 11 models across 4 presets. Fixed vendor violations: Gemini 3.x (0.1-0.5 → 1.0), Nemotron 3 Super (0.1-0.2 → 1.0), GLM-5.1 balanced orch (0.3 → 1.0), Qwen 3.6 Plus (0.2 → 0.6), Qwen 3 Coder (0.3 → 1.0). DeepSeek V3.2 and Claude kept at current conservative values. All changes synced live→repo.
- **2026-04-24 (GLM tuning)**: GLM-5.1 refined from uniform 1.0 to per-agent tuning based on task analysis: oracle 0.5 (precision reasoning), explorer 0.4 (consistent search), librarian 0.6 (doc synthesis), orchestrator 0.6 (balanced planning). Council master 0.6 (synthesis), diversity reviewers remain 1.0. Discovery: omo-slim hardcodes per-role temps (orch=0.1, explorer=0.1, etc.) that preset `temperature` overrides; `/models` switch does NOT re-apply temperature — only `/preset` command does.
- **2026-04-29 (DeepSeek V4 Pro fixed)**: `@ai-sdk/deepseek@2.0.30` shipped with changelog entry "fix(provider/deepseek): preserve reasoning_content for deepseek-v4 in multi-turn requests". Provider switched from `@ai-sdk/openai-compatible` to `@ai-sdk/deepseek` (dedicated). V4 Pro now fully stable for multi-turn agentic work with tool calls. Assigned as **orchestrator** and **oracle** in all presets. Temperature not set (thinking mode enforces own). All previous "not recommended" caveats removed.
- **2026-05-06 (GLM 5.1 thinking features)**: Full GLM thinking configuration: added `interleaved: {field: reasoning_content}` for multi-turn reasoning round-trip, `clear_thinking: false` for preserved thinking, output limit raised to 65536. Temperature now explicit on all agents (including thinking-mode models). Regenerated `oh-my-opencode-slim.json` from `model-profile.py` with fixes: websearch (Exa fallback) restored to AGENT_DEFAULTS, observer skills restored, `$schema` added, stale "tester" agent removed. `model-switch.md` rewritten with explicit temperature guidance. GLM API tested: preserved thinking confirmed (598 tokens with reasoning history vs 344 without, complete vs cut off). DeepSeek API tested: temperature fully ignored in thinking mode. OpenCode pipeline verified: `reasoning_content` reaches API as top-level field (bug fixed).
- **2026-04-29 (Config generation)**: Created `model-profile.jsonc` (57 lines) + `model-profile.py` (331 lines) + `oc --sync-profile` flag + `/model-switch` command. Reduces config edits from 457 lines of JSON to 57 lines of JSONC. 61% of the full config is now auto-generated boilerplate. Script uses zero dependencies, embedded agent defaults, and automatic temperature/Kimi thinking logic detection.
- **2026-05-02 (audio transcription — transcribe + audio-analysis skill)**: Created `~/.config/opencode/scripts/transcribe` — wraps whisper.cpp (Vulkan GPU, local) for speech-to-text from audio/video files. Built via `github:nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan` flake. Observer discovers via `audio-analysis` skill. Model (`ggml-large-v3-turbo`, 1.6 GB) shared at `~/.local/share/opencode/models/whisper/`. Updated AGENTS.md, config, wiki. Created `~/.config/opencode/scripts/analyze-video.py` — multi-provider video analysis script (Kimi K2.6 default, OpenRouter/Gemini for audio+visual). Zero dependencies. Observer discovers via `video-analysis` skill. MCP `video_analysis` retained as fallback for small clips (≤8MB). Updated vision-integration wiki with multi-provider video path documentation.
- **2026-05-02 (Kimi K2.6 video/audio research)**: Confirmed via official docs: K2.6 supports `video_url` content type natively (keyframe extraction from mp4/mpeg/mov/avi/flv/mpg/webm/wmv/3gpp, max 2K res). **No audio track analysis** — visual-only, not audiovisual. Updated observer role description and vision-integration wiki page with native video support details.
- **2026-04-29 (AGENTS.md rewrite)**: Trimmed from 135 to 109 lines applying industry research (Lost in the Middle fix: anti-loop moved to top, per-agent instructions added for all 7 roles, bash blob removed, "Never add filler text" as bright-line constraint). Added oracle decision commitment instructions and Z.AI concurrency warning.
- **2026-04-29 (Wiki de-duplication)**: Removed duplicate agent→model tables from 3 wiki pages. All model assignments reference `model-profile.jsonc` (canonical source). wiki-lint now only validates wiki-internal consistency (dead links, orphans, stale dates) — not config-vs-wiki drift.

## Output Limits

`maxTokens` in `oh-my-opencode-slim.json` is **dead config** — the plugin's `$strict` schema strips it during validation. It has no effect.

The real output limit mechanism is `limit.output` on model definitions in `opencode.json`:

| Model | limit.output | Why |
|-------|-------------|-----|
| kimi-for-coding (K2.6) | 262144 | Kimi coding endpoint default is low — explicit limit ensures full-length code generation |
| GLM-5.1 | 65536 | Z.AI Coding Plan — raised from 32768 (2026-05-06) for thinking headroom |
| Claude models | (provider default) | Defaults sufficient for bounded tasks |

OpenCode core may also cap output via `OUTPUT_TOKEN_MAX` (default 32000), which is independent of model-level limits.

## MCP Allocation Strategy

| MCP | Who gets it | Why |
|-----|------------|-----|
| `web-search-prime` | Orchestrator, oracle, designer, librarian | Z.AI — primary web search (GLM Coding Pro subscription) |
| `websearch` | Orchestrator, oracle, designer, librarian | Exa — fallback web search (HF token for higher quotas) |
| `context7` | Oracle, librarian, explorer, fixer, designer | Library docs — deep research |
| `grep_app` | Explorer, librarian | Parallel codebase search across open-source |
| `zai_vision` | Observer, Designer (premium/custom) | Observer: primary vision agent, Read-first with MCP fallback. Designer: retained on premium/custom for direct delegation. Repo: opt-in per-project. |

**Notable:** Orchestrator gets both `web-search-prime` and `websearch` — it delegates specialized research to other agents, but has its own web tools for discovery/decision-making. Visual content is routed to `@observer` (fact extraction), then optionally to `@designer` (creative work). Observer owns `zai_vision` MCP for video and Read fallback.

## Council Diversity Rules

For meaningful multi-model consensus:
1. **Master ≠ any reviewer** — master synthesizes, shouldn't be biased by its own prior output
2. **No duplicate reviewers** — each brings unique training data and failure modes
3. **Cross-provider diversity** — mix Anthropic, Google, DeepSeek, Qwen, Z.AI when possible
4. **4 distinct perspectives minimum** — fewer than 4 defeats the purpose of council

**Custom preset council (live):** GLM-5.1 (master) + Kimi K2.6 (reviewer-1) + DeepSeek V3.2 (reviewer-2) + Claude Sonnet 4 (reviewer-3) — 4 unique models from 4 distinct training lineages (Z.AI, Moonshot, DeepSeek, Anthropic).

## Loop Guard (Anti-Loop Rules)

Orchestrator must self-monitor for runaway behavior:

1. **Stop after 10+ consecutive turns** without completing the task — ask the user for direction
2. **Do not repeat the same tool call** with identical arguments — if the result didn't help, try a different approach or stop
3. **Stop after reading the same file more than twice** without making progress — escalate to the user

These rules complement the `todoContinuation.maxContinuations: 15` numeric cap by catching loops that don't hit the continuation limit.

## Model ID Format

Models use `provider/model-name` format:
- `openrouter/qwen/qwen3.6-plus` — Qwen via OpenRouter
- `anthropic/claude-sonnet-4-6` — Claude via direct Anthropic API (if configured)
- `openrouter/anthropic/claude-sonnet-4.6` — Claude via OpenRouter
- `openrouter/deepseek/deepseek-v3.2` — DeepSeek via OpenRouter
- `openrouter/z-ai/glm-5.1` — GLM via OpenRouter (Z.AI publishes there)
- `zai-coding-plan/glm-5.1` — GLM via Z.AI subscription

The `openrouter/` prefix routes through the OpenRouter provider (works for any model they host). Direct provider names (`anthropic/`, `deepseek/`) use dedicated API keys.

## Open Questions

- **Anti-hedging prompt:** Decision-making agents (oracle, orchestrator, council master) may benefit from a system prompt addition targeting verbose reasoning: *"Commit to the most likely explanation after examining evidence once. Do not re-analyze unless new information contradicts your conclusion."* Requires investigating omo-slim's `prompt`/`orchestratorPrompt` override fields.

## Related
- [[occams-code-setup]] — Architecture, config files, scripts
- [[troubleshooting]] — What to do when models fail
