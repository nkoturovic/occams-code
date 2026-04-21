---
summary: "Vision integration: Gemini native multimodal + Z.ai Vision MCP + GLM-5V-Turbo fallback"
type: concept
tags: [vision, designer, glm-5v-turbo, mcp, multimodal, zai]
sources: []
related:
  - agent-roles-and-models
  - design-systems
  - occams-code-setup
created: 2026-04-21
updated: 2026-04-21
confidence: high
---

# Vision Integration

## Architecture

Three layers, each solving a different problem:

| Layer | What | When it helps |
|-------|------|---------------|
| Gemini (native multimodal) | @designer sees images directly in context | Default — works out of the box |
| Z.ai Vision MCP | Tool-based image analysis: 8 tools for OCR, UI-to-code, diagrams, video, error diagnosis | Opt-in — structured analysis beyond native vision |
| GLM-5V-Turbo (fallback) | Purpose-built design-to-code model in fallback chain | Automatic — activates when Gemini models time out |

## How it works

- All shipped presets use Gemini for @designer (native multimodal — no setup needed)
- Vision MCP (`zai_vision`) is in opencode.json but disabled by default. Enable by adding Z.ai API key
- GLM-5V-Turbo is in the designer fallback chain (position 3), accessed via OpenRouter pay-as-you-go
- Per-project overrides can swap @designer to GLM-5V-Turbo as primary model for vision-heavy projects

## Vision MCP tools (8 total)

| Tool | Purpose |
|------|---------|
| `ui_to_artifact` | Screenshot → code, specs, or descriptions |
| `extract_text_from_screenshot` | OCR for code, terminals, docs |
| `diagnose_error_screenshot` | Visual bug analysis with fix suggestions |
| `understand_technical_diagram` | Architecture, flow, UML, ER diagrams |
| `analyze_data_visualization` | Charts and dashboards → insights |
| `ui_diff_check` | Compare two UI screenshots for drift |
| `image_analysis` | General-purpose image understanding |
| `video_analysis` | Video inspection (≤8 MB, MP4/MOV/M4V) |

## Cost structure

- Gemini native vision: included in OpenRouter per-token pricing (~$0.15/$0.60 per M tokens for Flash)
- Vision MCP: free with Z.ai Coding Plan subscription; rolling pool shared across all tiers
- GLM-5V-Turbo: $1.20/$4.00 per M tokens via OpenRouter (only when activated in fallback or override)

## Re-evaluation triggers

- If Z.ai adds GLM-5V-Turbo to Coding Plan Pro/Max → revisit to use subscription quota
- If Vision MCP upgrades from GLM-4.6V to GLM-5V-Turbo → may eliminate need for separate model
- If OpenCode adds native image-to-model passthrough for MCP → simplify workflow

## Related
- [[design-systems]] — DESIGN.md text-based design systems (complementary to vision)
- [[agent-roles-and-models]] — Designer agent role and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
