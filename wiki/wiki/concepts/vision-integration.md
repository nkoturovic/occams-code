---
summary: "Non-text content routing: @observer for fact extraction, @designer for creative UI/UX work. Native Read + zai_vision MCP fallback."
type: concept
tags: [vision, observer, designer, multimodal, mcp, zai, gemini, kimi]
sources: []
related:
  - agent-roles-and-models
  - occams-code-setup
created: 2026-04-21
updated: 2026-04-23
confidence: high
---

# Non-text Content

## Content type support

| Content | Read tool | Vision MCP tools | Webfetch |
|---------|-----------|-----------------|----------|
| Images | ✅ base64 attachment (model-dependent delivery) | ✅ All image tools | ✅ Returns attachment |
| PDF | ✅ base64 attachment (model-dependent delivery) | ✅ image_analysis, extract_text | ❌ Garbles binary |
| SVG | ✅ Text (XML) | ✅ image_analysis for visual | ✅ Returns text |
| Video | ❌ Binary error | ✅ video_analysis ≤8MB | ❌ |
| Audio | ❌ Binary error | ❌ No tool | ❌ |

**Routing:** Orchestrator is text-only. Images, PDFs, video → `@observer` (fact extraction). Design work → `@designer` (creative, works from observer's text output).

**@observer tool priority:**
- Images/PDFs → Read first (native multimodal). `zai_vision` MCP as fallback.
- Video → `zai_vision` MCP → `video_analysis` (opt-in per-project, not enabled by default)
- Audio → not supported (no tool available)

## Architecture

OpenCode is TypeScript. The Read tool (`read.ts`) base64-encodes images and returns them as attachments. **Whether the model actually receives them depends on provider integration.**

The `@ai-sdk/openai-compatible` provider (used by OpenRouter) strips media from tool results and re-injects them as synthetic user messages. This re-injection is model-dependent:
- **Gemini models**: ✅ process re-injected media correctly
- **GLM-5V-Turbo**: ❌ returns "Cannot read image" error — model-specific failure

**User message images are NOT affected** by `supportsMediaInToolResults`. Inline-pasted images flow directly to multimodal models without the tool-result stripping issue.

## Delivery paths

| Method | Works? | Notes |
|--------|--------|-------|
| File on disk → delegate to @observer | ✅ | Read tool delivers base64. Kimi K2.6 / Gemini process it. |
| URL → `curl` to disk → delegate | ✅ | Use `curl -sL "URL" -o /tmp/file.ext"`, not webfetch for binary. |
| Inline paste → DB extract → delegate | ✅ | AGENTS.md has extraction commands. |
| Inline paste → multimodal orchestrator | ✅ | Works with Gemini. GLM-5V-Turbo fails. |
| Read tool → text-only model | ❌ | Model can't process visual content. |
| Video/audio → MCP | ⚠️ | `video_analysis` for video ≤8MB. No audio tool. |

## Per-preset models

| Preset | @observer | @designer |
|--------|-----------|-----------|
| `cheap` | `gemini-3-flash-preview` | `gemini-3-flash-preview` |
| `balanced` | `kimi-k2.6` | `gemini-3-flash-preview` |
| `premium` | `kimi-k2.6` | `kimi-k2.6` |

Observer: temp 0.1 (deterministic). Designer: temp 0.5 (creative). Both multimodal. Observer uses Read tool first, `zai_vision` MCP as fallback.

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

**Status varies by config:**
- **Live (all presets):** `enabled: true` in opencode.json, assigned to observer mcps (all presets). Observer uses Read for images/PDFs; MCP for video and Read fallback. Designer retains MCP on premium/custom for direct delegation.
- **Repo (all presets):** `enabled: false` in opencode.json. Opt-in per-project: set `enabled: true` in opencode.json AND add `"zai_vision"` to observer's `mcps` array.

8 tools, needs API key:

| Tool | Purpose | Tested? |
|------|---------|---------|
| `ui_to_artifact` | Screenshot → code, specs, or descriptions | No |
| `extract_text_from_screenshot` | OCR for code, terminals, docs | No |
| `diagnose_error_screenshot` | Visual bug analysis with fix suggestions | No |
| `understand_technical_diagram` | Architecture, flow, UML, ER diagrams | No |
| `analyze_data_visualization` | Charts and dashboards → insights | No |
| `ui_diff_check` | Compare two UI screenshots for drift | No |
| `image_analysis` | General-purpose image understanding | No |
| `video_analysis` | Video inspection (≤8 MB, MP4/MOV/M4V) | No |

MCP connectivity confirmed. Timeout: 300000ms (5min).

## Known limitations

- Video/audio cannot be ingested via Read tool — video needs `video_analysis` MCP, audio has no tool
- `webfetch` garbles PDFs and other binary — use `curl` instead
- DB extraction `ORDER BY id DESC LIMIT 1` may extract from wrong session if concurrent (low risk)
- OpenCode loads AGENTS.md into ALL agents. Per-role scoping in the "Non-text Content" section ensures observer reads, designer creates.

## Related
- [[agent-roles-and-models]] — Observer + designer agent roles and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
