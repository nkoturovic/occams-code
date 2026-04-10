---
summary: "Per-agent design rationale, delegation strategy, model selection criteria, and MCP allocation"
type: concept
tags: [occams-code, opencode, agents, models, delegation]
sources: []
related:
  - occams-code-setup
  - troubleshooting
created: 2026-04-10
updated: 2026-04-10
confidence: high
---

# Agent Roles and Model Selection

## The 7 Roles

| Role | Purpose | Call frequency | Cost sensitivity |
|------|---------|---------------|-----------------|
| **Orchestrator** | Master delegator, strategic coordinator | Every message | Low — best available justified |
| **Oracle** | Deep reasoning, architecture, code review | Infrequent, high-stakes | Low — quality over cost |
| **Designer** | UI/UX, visual polish, responsive layouts | Moderate | Medium — needs multimodal |
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
- UI/UX polish → `@designer` (visual intent)
- Critical decisions → `@council` (multi-perspective)

**Don't delegate when:**
- Single small change (<20 lines, one file)
- You already have the file in context
- Explaining takes longer than doing

## Model Selection Criteria Per Role

### Orchestrator — Best reasoning + instruction following
Needs: complex delegation decisions, multi-step planning, understanding when to delegate vs do it yourself. Top-tier reasoning is non-negotiable.
- Best: Claude Sonnet 4, GLM-5.1
- Acceptable: Qwen 3.6 Plus, DeepSeek V3.2

### Oracle — Strongest reasoning, lowest hallucination
Needs: architecture decisions, complex debugging, code review. Infrequent but high-stakes — quality justifies cost.
- Best: Claude Opus 4, Claude Sonnet 4, Gemini 3.1 Pro
- Acceptable: GLM-5.1 (strong reasoning, open-source)

### Designer — Multimodal capability + creativity
Needs: screenshot analysis, CSS/layout reasoning, responsive design, accessibility. Must support vision input.
- Best: Gemini 3 Flash/Pro (native multimodal), Claude Sonnet 4
- Temperature: 0.5 (higher than other roles — creative exploration)

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

| Role | Temperature | Why |
|------|-----------|-----|
| Orchestrator | 0.3 | Balanced reasoning — creative enough to find solutions, precise enough to delegate correctly |
| Oracle | 0.2 | Precise analysis — minimize hallucination in high-stakes decisions |
| Designer | 0.5 | Creative exploration — UI/UX benefits from more varied suggestions |
| Explorer | 0.1 | Deterministic search — same query should find same files |
| Librarian | 0.2 | Accurate synthesis — docs require precision, not creativity |
| Fixer | 0.1 | Deterministic edits — code changes should be exact, not creative |

## MCP Allocation Strategy

| MCP | Who gets it | Why |
|-----|------------|-----|
| `websearch` | Everyone except designer | General-purpose web lookup |
| `context7` | Oracle, librarian, explorer, fixer | Library docs — deep research |
| `grep_app` | Explorer, librarian | Parallel codebase search across open-source |
| `semantic_search` | Oracle, designer, explorer, librarian, fixer | Local project code index (requires `uv`) |

**Notable:** Orchestrator only gets `websearch` — it delegates specialized research to other agents. Designer gets `semantic_search` for understanding existing codebase patterns.

## Council Diversity Rules

For meaningful multi-model consensus:
1. **Master ≠ any reviewer** — master synthesizes, shouldn't be biased by its own prior output
2. **No duplicate reviewers** — each brings unique training data and failure modes
3. **Cross-provider diversity** — mix Anthropic, Google, DeepSeek, Qwen, Z.AI when possible
4. **4 distinct perspectives minimum** — fewer than 4 defeats the purpose of council

## Model ID Format

Models use `provider/model-name` format:
- `openrouter/qwen/qwen3.6-plus` — Qwen via OpenRouter
- `anthropic/claude-sonnet-4-6` — Claude via direct Anthropic API (if configured)
- `openrouter/anthropic/claude-sonnet-4-6` — Claude via OpenRouter
- `z-ai/glm-5.1` — GLM via OpenRouter (Z.AI publishes there)
- `zai-coding-plan/glm-5.1` — GLM via Z.AI subscription

The `openrouter/` prefix routes through the OpenRouter provider (works for any model they host). Direct provider names (`anthropic/`, `deepseek/`) use dedicated API keys.

## Related
- [[occams-code-setup]] — Architecture, config files, scripts
- [[troubleshooting]] — What to do when models fail
