---
summary: "Non-text content handling: images, PDFs via @designer. Per-preset models, tested delivery paths, MCP tools."
type: concept
tags: [vision, designer, multimodal, mcp, zai, gemini]
sources: []
related:
  - agent-roles-and-models
  - occams-code-setup
created: 2026-04-21
updated: 2026-04-22
confidence: high
---

# Non-text Content

## Content type support

| Content | Orchestrator (text-only) | @designer (multimodal) | Read tool |
|---------|-------------------------|----------------------|-----------|
| Images (png, jpg, gif, webp, svg, bmp, ico, tiff, avif) | ❌ | ✅ native | ✅ attachment |
| PDFs | ❌ (delivered, not interpreted) | ✅ (model-dependent) | ✅ attachment |
| Video | ❌ | ⚠️ API supports, Read tool doesn't | ❌ |
| Audio | ❌ | ⚠️ API supports, Read tool doesn't | ❌ |

Same routing applies to all: **file on disk → delegate path to @designer.** Do NOT attempt to Read non-text files yourself.

## Delivery paths (tested 2026-04-22)

| Method | Works? | Notes |
|--------|--------|-------|
| File on disk → delegate to @designer | ✅ | Orchestrator routing validated (test #2). @designer reads via native multimodal. |
| URL to image/PDF → webfetch → delegate | ✅ | `webfetch save_binary=true` downloads to disk → delegate path |
| Inline paste → DB extract → delegate | ✅ (extraction) | AGENTS.md has extraction commands for images and PDFs |
| Inline paste → forward to subagent | ❌ | Platform limitation — binary not forwarded |
| Video/audio file on disk | ⚠️ | Read tool cannot ingest. Needs `zai_vision` MCP or external tools |
| zai_vision MCP tools | ⚠️ | Connectivity confirmed. Reliability issues: 2/3 calls timed out at default 30s timeout. Fixed by adding `"timeout": 300000` to MCP config. |

## Per-preset designer models

| Preset | Designer model | Multimodal? |
|--------|---------------|-------------|
| `cheap` | `openrouter/google/gemini-3-flash-preview` | Yes |
| `balanced` | `openrouter/google/gemini-3-flash-preview` | Yes |
| `premium` | `openrouter/google/gemini-3.1-pro-preview` | Yes |

All multimodal. Do not assume a specific model — check `oh-my-opencode-slim.json`.

## Z.ai Vision MCP (opt-in)

8 tools, needs API key (`opencode.json` → `mcp.zai_vision`):

| Tool | Purpose | Tested? |
|------|---------|---------|
| `ui_to_artifact` | Screenshot → code, specs, or descriptions | No |
| `extract_text_from_screenshot` | OCR for code, terminals, docs | No |
| `diagnose_error_screenshot` | Visual bug analysis with fix suggestions | No |
| `understand_technical_diagram` | Architecture, flow, UML, ER diagrams | No |
| `analyze_data_visualization` | Charts and dashboards → insights | No |
| `ui_diff_check` | Compare two UI screenshots for drift | No |
| `image_analysis` | General-purpose image understanding | Reachable, no image data tested |
| `video_analysis` | Video inspection (≤8 MB, MP4/MOV/M4V) | No |

MCP connectivity confirmed (tool invocation succeeded). Output quality unvalidated.

## Known limitations

- OpenCode loads AGENTS.md into ALL agents (not just orchestrator). Previously, @designer followed orchestrator rules ("NEVER Read images") and bypassed native multimodal in favor of MCP tools. **Fixed:** AGENTS.md now scopes instructions per agent role.
- zai_vision MCP has timeout issues at default 30s. Vision analysis via Z.ai API (glm-4.6v with thinking) can take >30s. **Fixed:** added `"timeout": 300000` (5min) to MCP config in opencode.json.
- Video/audio cannot be ingested via Read tool — needs MCP or external tools.
- DB extraction uses `ORDER BY id DESC LIMIT 1` — in concurrent sessions, may extract from wrong session. Low risk in typical single-session use.

## Related
- [[agent-roles-and-models]] — Designer agent role and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
