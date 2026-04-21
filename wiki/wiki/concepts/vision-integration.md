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

## Vendor independence

Z.ai coupling is shallow — every reference is a config string, no code dependency, no custom scripts. Dropping or replacing Z.ai is a find-and-replace across 2 JSON files.

### What to change if dropping Z.ai

| File | What to remove | Replace with |
|------|---------------|--------------|
| `opencode.json` → `mcp.zai_vision` | Delete entire `zai_vision` block | Another vision MCP or nothing (Gemini native vision still works) |
| `opencode.json` → `provider.openrouter.models` | Remove `z-ai/glm-5.1`, `z-ai/glm-5v-turbo` entries | Alternative vision model entries |
| `oh-my-opencode-slim.json` → designer mcps | Remove `"zai_vision"` from mcps arrays | New MCP name or leave removed |
| `oh-my-opencode-slim.json` → fallback chains | Replace `openrouter/z-ai/*` model IDs | Alternative model IDs |
| `oh-my-opencode-slim.json` → council | Replace `openrouter/z-ai/*` model IDs | Alternative model IDs |

### Vision alternatives (no Z.ai)

| Alternative | What changes | Trade-off |
|-------------|-------------|-----------|
| **Gemini only** (current default) | Remove MCP block, remove GLM-5V-Turbo from chains | No structured vision tools, but native multimodal still works |
| **Claude as designer** | Change designer model to `openrouter/anthropic/claude-sonnet-4-6` | Strong vision, higher cost |
| **Different vision MCP** | Replace `zai_vision` block with new MCP config | Depends on MCP ecosystem |
| **OpenRouter-only GLM** | Keep `openrouter/z-ai/*` models, drop MCP + subscription | Models still available pay-per-token via OpenRouter |

**Key insight:** The vision architecture is layered on purpose. Gemini native multimodal works without any Z.ai dependency. The MCP and GLM-5V-Turbo are enhancements, not requirements. The setup degrades gracefully — remove Z.ai entirely and the designer still sees images via Gemini.

## Related
- [[design-systems]] — DESIGN.md text-based design systems (complementary to vision)
- [[agent-roles-and-models]] — Designer agent role and model selection
- [[occams-code-setup]] — Two-config system, per-project overrides
