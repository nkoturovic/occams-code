---
summary: "Non-text content handling: images, PDFs via @designer MCP tools. Per-preset models, tested delivery paths, future re-evaluation plan."
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

| Content | Orchestrator (text-only) | @designer via MCP tools | Read tool |
|---------|-------------------------|----------------------|-----------|
| Images (png, jpg, gif, webp, svg, bmp, ico, tiff, avif) | ❌ | ✅ MCP reads from disk | ❌ Returns text error (`// TODO: handle images`) |
| PDFs | ❌ | ✅ MCP reads from disk | ❌ Same as images |
| Video | ❌ | ⚠️ `video_analysis` tool | ❌ |
| Audio | ❌ | ❌ No MCP tool available | ❌ |

Same routing applies to all: **file on disk → delegate path to @designer.** Do NOT attempt to Read non-text files yourself.

## Architecture reality (tested 2026-04-22)

**The Read tool cannot deliver images to models.** The Go server's `view.go` has `// TODO: handle images` — it returns a text error for image files. Images only flow in User messages (inline paste), never in tool results (`ToolResult.Content` is `string` only).

This means @designer's native multimodal capability is unused for file-on-disk scenarios. All vision analysis goes through `zai_vision` MCP tools, which send images to Z.ai's API (glm-4.6v with thinking) independently.

**Implication:** @designer does not need to be a multimodal model when using MCP tools. Any model that can call MCP tools and reason about text results works. However, keeping a multimodal model is recommended for future-proofing — if OpenCode implements image Read support, native multimodal will be faster than MCP roundtrips.

## Delivery paths (tested 2026-04-22)

| Method | Works? | Notes |
|--------|--------|-------|
| File on disk → delegate to @designer | ✅ | Orchestrator routing validated. @designer analyzes via `zai_vision` MCP tools. |
| URL to image/PDF → webfetch → delegate | ✅ | `webfetch save_binary=true` downloads to disk → delegate path → MCP tool |
| Inline paste → DB extract → delegate | ✅ (extraction) | AGENTS.md has extraction commands for images and PDFs. MCP tool reads extracted file. |
| Inline paste → forward to subagent | ❌ | Platform limitation — binary not forwarded |
| Video/audio file on disk | ⚠️ | `video_analysis` MCP tool for video. No audio tool available. |
| zai_vision MCP tools | ✅ | Connectivity confirmed. Timeout fixed (300000ms). 1 tool tested with data (`image_analysis`). |

## Per-preset designer models

| Preset | Designer model | Multimodal? | Vision via |
|--------|---------------|-------------|------------|
| `cheap` | `openrouter/google/gemini-3-flash-preview` | Yes | MCP tools (native multimodal when Read supports images) |
| `balanced` | `openrouter/google/gemini-3-flash-preview` | Yes | MCP tools (native multimodal when Read supports images) |
| `premium` | `openrouter/google/gemini-3.1-pro-preview` | Yes | MCP tools (native multimodal when Read supports images) |

Model choice doesn't affect vision capability today — MCP tools handle all image analysis independently. A multimodal model is recommended for future-proofing.

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
- zai_vision MCP had timeout issues at default 30s. Vision analysis via Z.ai API (glm-4.6v with thinking) can take >30s. **Fixed:** added `"timeout": 300000` (5min) to MCP config in opencode.json.
- Video/audio cannot be ingested via Read tool — needs MCP or external tools.
- DB extraction uses `ORDER BY id DESC LIMIT 1` — in concurrent sessions, may extract from wrong session. Low risk in typical single-session use.

## ⚠️ FUTURE RE-EVALUATION — HIGH IMPORTANCE

**When OpenCode's Read tool adds image delivery support** (the Go source has `// TODO: handle images` in `view.go`), the architecture should be re-evaluated:

1. **Switch @designer to a multimodal model** — native multimodal is faster (no MCP roundtrip) and cheaper (no separate API call). All shipped presets already have multimodal designers (Gemini).
2. **Update AGENTS.md** — change @designer instructions from "use MCP tools" back to "use Read tool first, MCP for structured analysis only."
3. **Keep MCP tools as enhancement** — for structured tasks (OCR, UI-to-code, diagram parsing) where specialized prompts outperform general multimodal.
4. **If using a text-only designer model (e.g., for cost savings), switch back to multimodal.**

**Why this matters:** MCP tools add latency (~30s+ per call even with timeout fix) and depend on Z.ai API availability. Native multimodal via Read would be near-instant and work offline (for local models). The entire MCP-first architecture is a workaround for the Read tool's incomplete implementation.

**Detection:** Check the OpenCode changelog or source for the `// TODO: handle images` being resolved. Also test: delegate an image path to @designer — if Read returns visual content (not a text error), the TODO is implemented.

## Related
- [[agent-roles-and-models]] — Designer agent role and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
