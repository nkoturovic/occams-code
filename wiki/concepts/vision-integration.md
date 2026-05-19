---
summary: "Non-text content routing: observer for visual (video) and audio (speech-to-text) analysis. Two scripts, two skills, one agent."
type: concept
tags: [vision, observer, designer, multimodal, mcp, zai, gemini]
sources:
  - raw/user/prompts/20260422-000304-first-vision-report.md
related:
  - agent-roles-and-models
  - occams-code-setup
created: 2026-04-21
updated: 2026-05-03
confidence: high
---

# Non-text Content

## Content type support

| Content | Read tool | Vision MCP tools | Webfetch |
|---------|-----------|-----------------|----------|
| Images | ✅ base64 attachment (model-dependent delivery) | ✅ All image tools | ✅ Returns attachment |
| PDF | ✅ base64 attachment (model-dependent delivery) | ✅ image_analysis, extract_text | ❌ Garbles binary |
| SVG | ✅ Text (XML) | ✅ image_analysis for visual | ✅ Returns text |
| Video | ❌ Binary error | ✅ `analyze-video.py` script (OpenRouter → Gemini native) → `video_analysis` MCP fallback | ❌ |
| Audio | ❌ Binary error | ✅ `transcribe` script (whisper.cpp local) — speech-to-text with SRT timestamps | ❌ |


**Routing:** Orchestrator is text-only. Images, PDFs, video, and audio go through `@observer` (fact extraction). Design work → `@designer` (creative, works from observer's text output).

**@observer tool priority:**
- Images/PDFs → Read first (native multimodal). `zai_vision` MCP as fallback.
- Video → `analyze-video.py` script (OpenRouter → Gemini for audio+visual). `video_analysis` MCP as fallback (≤8MB). Load `video-analysis` skill for auto-discovery.
- Audio → `transcribe` script (whisper.cpp local). Load `audio-analysis` skill for auto-discovery.
- **Combined pipeline:** For lecture notes, load `lecture-notes` skill — full 8-phase workflow.

## Video Analysis Pipeline

### Why native video doesn't work through OpenCode

OpenCode's Read tool rejects all video files as binary (`read.ts:243: "Cannot read binary file"`). The pipeline has blockers at multiple layers:

| Layer | File | Issue |
|---|---|---|
| Read tool | `tool/read.ts:21` | Only `image/jpeg`, `image/png`, `image/gif`, `image/webp` in `SUPPORTED_IMAGE_MIMES` |
| Read tool | `tool/read.ts:243` | `isBinaryFile()` hits before video attachment path could run |
| Media detection | `util/media.ts:7` | `isMedia()` returns false for `video/*` — only `image/*` + `application/pdf` |
| Magic byte sniffing | `util/media.ts:15` | Only detects PNG/JPEG/GIF/BMP/PDF magic bytes |
| Content parts | `session/message-v2.ts:877` | `isMedia()` filter excludes video from content part construction |

Even if OpenCode layers were fixed, the Vercel AI SDK's Anthropic provider converts `type: "media"` to Anthropic content blocks, which have no `video_url` type — only `image` and `text`. Kimi's API adds `video_url` as an extension, but upstream SDK doesn't know about it. This is moot — we use OpenRouter/Gemini directly via the script, bypassing the SDK entirely.

**Verdict:** Native video through the Read tool is blocked at OpenCode + AI SDK layers. Not worth patching — MCP path is production-ready.

### Working paths

#### Path A: `analyze-video.py` (recommended)

The `analyze-video.py` script sends video directly to a multimodal LLM via `video_url` content type — the model processes the video natively, not via a separate pipeline:

```
User's video file → orchestrator delegates to @observer
→ observer runs: python3 ~/.config/opencode/scripts/analyze-video.py /tmp/video.mp4
→ Gemini processes video natively (audio+visual) → returns text analysis
→ observer reports findings back to orchestrator
```

**Single provider:** OpenRouter → Gemini. Default model: `~google/gemini-pro-latest` (auto-upgrades, currently 3.1 Pro Preview). Override with `-m`.

- **Video format:** mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp
- **Max size:** 20MB inline base64
- **Audio:** Yes — Gemini processes both audio and visual streams (1fps sampling + 1Kbps audio)
- **Zero deps:** stdlib only — `urllib` + `json` + `base64`
- **Discovery:** Load `video-analysis` skill (`/skill video-analysis`) or instruct observer directly.

#### Path B: MCP `video_analysis` (fallback)

```
User's video file → orchestrator delegates to @observer
→ observer uses zai_vision MCP tool: video_analysis(filePath="/tmp/video.mp4")
→ MCP server processes video server-side → returns structured text observations
→ observer reports findings back to orchestrator
```

- **Limitations:** ≤8 MB, mp4/mov/m4v only.
- **Quality:** Z.AI's proprietary vision pipeline processes video, Kimi receives text description. Lower quality ceiling than native.
- **When to use:** Quick checks, small clips, when script not available.

### Delegation pattern

Orchestrator should tell observer:
> "Analyze the video at `/path/to/video.mp4` using the `video_analysis` MCP tool. Describe what happens, key UI elements, and any visible text."

Observer has `video_analysis` in its MCP tools via `zai_vision` — enabled in all presets (live).

## Audio Pipeline

### Working path: `transcribe` (local whisper.cpp)

The `transcribe` script wraps whisper.cpp with Vulkan GPU acceleration via a Nix flake from [kotur-nixpkgs](https://github.com/nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan):

```
User's audio/video file → orchestrator delegates to @observer
→ observer runs: ~/.config/opencode/scripts/transcribe /tmp/lecture.mp4 --language sr
→ ffmpeg extracts 16kHz mono WAV from video (if needed)
→ whisper-cli (Vulkan GPU + Zen 4 AVX-512 CPU) transcribes speech
→ outputs SRT with timestamps (default) or any whisper-cli format
→ observer reports text/transcript back to orchestrator
```

- **Model:** `ggml-large-v3-turbo` (1.6 GB, best Serbian accuracy). Stored at `~/.local/share/opencode/models/whisper/` (XDG data, not in git). Auto-downloaded on first use.
- **Performance:** CPU (Zen 4 AVX-512) ~0.5x realtime, Vulkan GPU (AMD Radeon 860M, RADV) ~8x realtime — confirmed working via `VK_ICD_FILENAMES` and `LD_LIBRARY_PATH` env vars set by the script. GPU successfully detected by whisper.cpp (not blocked by nix sandbox on this machine). Encode time: 6.4x faster on GPU vs CPU.
- **Discovery:** Load `audio-analysis` skill (`/skill audio-analysis`) or instruct observer directly.
- **Flake:** `$OCCAM_WHISPER_FLAKE_LOCAL#whisper-cpp-vulkan` or `~/repos/kotur-nixpkgs#whisper-cpp-vulkan` if present, otherwise `github:nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan`

### Audio + Video combined pipeline

For lectures with distinct slide sections and spoken content:
1. `transcribe lecture.mp4 --language sr` → full transcript with timestamps
2. `analyze-video.py lecture.mp4` → visual slide content
3. Merge by timestamp into Obsidian notes

**Full pipeline example (64-minute Serbian lecture):** 1. `transcribe lecture.mp4 --language sr` → SRT in CWD. 2. Extract keyframes, scout with @observer for slide boundaries. 3. OCR slide frames with @observer. 4. Merge → `Predavanje NN.md` with embedded images, LaTeX math, Serbian text. See [[nmo]] for the complete project and processed lectures.

### Alternatives

| Method | Pros | Cons |
|---|---|---|
| **transcribe (local)** | Free, offline, fast on this hardware | Needs nix + 1.6GB model download |
| openai-whisper (Python) | Python API, CUDA/ROCm | 5GB deps, no ROCm on Radeon 860M iGPU |
| OpenRouter STT API | No setup, cloud | Pay per second, needs network |

## Architecture

OpenCode is TypeScript. The Read tool (`read.ts`) base64-encodes images and returns them as attachments. **Whether the model actually receives them depends on provider integration.**

The `@ai-sdk/openai-compatible` provider (used by OpenRouter) strips media from tool results and re-injects them as synthetic user messages. This re-injection is model-dependent:
- **Gemini models**: ✅ process re-injected media correctly
- **GLM-5V-Turbo**: ❌ returns "Cannot read image" error — model-specific failure

**User message images are NOT affected** by `supportsMediaInToolResults`. Inline-pasted images flow directly to multimodal models without the tool-result stripping issue.

## Delivery paths

| Method | Works? | Notes |
|--------|--------|-------|
| File on disk → delegate to @observer | ✅ | Read tool delivers base64. Observer model processes it. |
| URL → `curl` to disk → delegate | ✅ | Use `curl -sL "URL" -o /tmp/file.ext"`, not webfetch for binary. |
| Inline paste → DB extract → delegate | ✅ | AGENTS.md has extraction commands. |
| Inline paste → multimodal orchestrator | ✅ | Works with Gemini. GLM-5V-Turbo fails. |
| Read tool → text-only model | ❌ | Model can't process visual content. |
| Video → MCP | ✅ | `video_analysis` MCP (≤8MB). Observer uses file path. No Read tool dependency. |
| Audio → whisper | ⚠️ | Extract audio via `ffmpeg`, transcribe with `whisper` CLI (local). |

## Per-preset models

| Preset | @observer | @designer |
|--------|-----------|-----------|
| `cheap` | `~gemini-flash-latest` | `gemini-3-flash-preview` |
| `balanced` | `~gemini-flash-latest` | `gemini-3-flash-preview` |
| `premium` | `~gemini-pro-latest` | `gemini-3.1-pro-preview` |
| `custom` (live) | `~gemini-pro-latest` | `kimi-k2.6` |

Observer: temp 1.0 (vendor recommended). Designer: temp varies per model. Both multimodal. Observer uses Read tool first for images/PDFs, `analyze-video.py` for video, `zai_vision` MCP as fallback.

## Inline paste extraction (from OpenCode DB)

When a user pastes an image/PDF inline (no file on disk), extract from the session database:

**Image:**
```bash
mime=$(sqlite3 ~/.local/share/opencode/opencode.db "SELECT json_extract(data, '$.mime') FROM part WHERE json_extract(data, '$.mime') LIKE 'image%' ORDER BY id DESC LIMIT 1" | sed 's|image/||') && sqlite3 ~/.local/share/opencode/opencode.db "SELECT json_extract(data, '$.url') FROM part WHERE json_extract(data, '$.mime') LIKE 'image%' ORDER BY id DESC LIMIT 1" | sed 's/^data:image\/[^;]*;base64,//' | base64 -d > /tmp/opencode-inline.$mime && echo "/tmp/opencode-inline.$mime"
```

**PDF:**
```bash
sqlite3 ~/.local/share/opencode/opencode.db "SELECT json_extract(data, '$.url') FROM part WHERE json_extract(data, '$.mime') = 'application/pdf' ORDER BY id DESC LIMIT 1" | sed 's/^data:application\/pdf;base64,//' | base64 -d > /tmp/opencode-inline.pdf && echo "/tmp/opencode-inline.pdf"
```

Caveat: `ORDER BY id DESC LIMIT 1` may extract from a different session if multiple sessions run concurrently.

## Z.ai Vision MCP

**Status:** ships in `opencode.json` without hardcoded secrets, using `Z_AI_API_KEY` from the environment. Observer uses Read for images/PDFs; MCP remains a fallback for video and image/PDF edge cases when the key is configured.

8 tools, needs API key:

| Tool | Purpose | Tested? |
|------|---------|---------|
| `ui_to_artifact` | Screenshot → code, specs, or descriptions | No |
| `extract_text_from_screenshot` | OCR for code, terminals, docs | No |
| `diagnose_error_screenshot` | Visual bug analysis with fix suggestions | No |
| `understand_technical_diagram` | Architecture, flow, UML, ER diagrams | No |
| `analyze_data_visualization` | Charts and dashboards → insights | No |
| `ui_diff_check` | Compare two UI screenshots for drift | No |
| `image_analysis` | General-purpose image understanding | ✅ Tested |
| `video_analysis` | Video inspection (≤8 MB, MP4/MOV/M4V) | No |

MCP connectivity confirmed. `image_analysis` tested with detailed output. Timeout: 300000ms (5min).

## Vendor independence

| Component | Z.ai-specific? | Replacement path |
|-----------|---------------|-----------------|
| Designer model (varies by preset) | No — OpenRouter | Swap to any multimodal model |
| zai_vision MCP | Optional by key | Ships without hardcoded secrets; active only when `Z_AI_API_KEY` is configured. Replace with ai-vision-mcp (Gemini) or mcp-vision (Ollama) |
| Other agents (GLM-5.1) | Model string only | Swap to any model |

**No hard Z.ai dependency for basic use.** The MCP is inert without `Z_AI_API_KEY`; everything else is model-string swaps.

## Test Results (2026-04-22)

| Date | Test | Model | Provider | Saw content? | Notes |
|------|------|-------|----------|-------------|-------|
| 2026-04-22 | Image via Read only | glm-5v-turbo | OpenRouter | ❌ NO | "Cannot read image" error. Model-specific. |
| 2026-04-22 | Image via zai_vision MCP | glm-4.6v (MCP) | Z.ai API | ✅ YES | Detailed description. |
| 2026-04-22 | PDF via Read | glm-5v-turbo | OpenRouter | ⚠️ Partial | Text extraction only, no visual. |
| 2026-04-22 | Inline paste → orchestrator | gemini-3.1-pro-preview | OpenRouter | ✅ YES | Successfully perceived inline pasted image. |
| 2026-04-22 | Read from path → orchestrator | gemini-3.1-pro-preview | OpenRouter | ✅ YES | Read tool works with Gemini. Model-specific, not platform-wide. |

**Key findings:**
1. Read tool delivers images to supported models (Gemini ✅, GLM-5V-Turbo ❌).
2. Inline paste delivers images to supported models directly — no tool-result stripping.
3. MCP tools remain useful for video analysis when enabled per-project.

## Future-proofing watch list

- OpenCode adds `supportsMediaInToolResults` to `@ai-sdk/openai-compatible` → Read delivers images natively to ALL models
- Z.ai adds GLM-5V-Turbo to Coding Plan → switch designer from OpenRouter to Coding Plan
- Alternative vision MCPs mature → test as backup
- New design-to-code models → swap via fallback chain

## Known limitations

- Video/audio cannot be ingested via Read tool — video needs `video_analysis` MCP, audio has no tool
- `webfetch` garbles PDFs and other binary — use `curl` instead
- DB extraction `ORDER BY id DESC LIMIT 1` may extract from wrong session if concurrent (low risk)
- OpenCode loads AGENTS.md into ALL agents. Per-role scoping in the "Non-text Content" section ensures observer reads, designer creates.

## Related
- [[agent-roles-and-models]] — Observer + designer agent roles and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
