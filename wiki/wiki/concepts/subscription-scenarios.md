---
summary: "Quick-switch reference: custom preset configurations for different subscription combos (Z.ai + Kimi, Z.ai only, Kimi only)"
type: concept
tags: [occams-code, opencode, models, presets, subscription]
sources: []
related:
  - occams-code-setup
  - agent-roles-and-models
created: 2026-04-24
updated: 2026-04-24
confidence: high
---

# Subscription Scenarios — Quick-Switch Reference

Quick-reference for reconfiguring the custom preset when subscriptions change. Edit `oh-my-opencode-slim.json` (live: `~/.config/opencode/`, repo: `~/personal/repos/occams-code/config/`).

## Available Models Per Subscription

### Z.ai Coding Plan
- **GLM-5.1** — flagship reasoning (text only)
- **GLM-5-Turbo** — fast, lighter reasoning (text only)
- **GLM-4.7** — previous generation (text only)
- **GLM-4.5-Air** — lightweight (text only)
- ❌ No vision model (GLM-5V-Turbo is NOT on Coding Plan)

### Kimi for Coding Plan ($39/mo)
- **Kimi K2.6** — multimodal (text + image + video), 262K context
- Thinking ON: temperature 1.0, top-p 1.0 (Moonshot official, confirmed in K2.6 blog)
- Thinking OFF: temperature 0.6 (coding endpoint default)
- Client-side temperature is ignored — API enforces its own value
- Anthropic Messages API compatible

### OpenRouter (pay-per-token, always available)
- `openrouter/z-ai/glm-5v-turbo` — GLM vision variant
- `openrouter/google/gemini-3-flash-preview` — cheap multimodal
- `openrouter/google/gemini-3.1-pro-preview` — premium multimodal
- `openrouter/moonshotai/kimi-k2.6` — Kimi via OpenRouter
- `openrouter/deepseek/deepseek-v3.2` — excellent coding, cheap
- `openrouter/qwen/qwen3.6-plus` — broad knowledge
- `openrouter/qwen/qwen3-coder:free` — free safety net

### DeepSeek API
- **DeepSeek V4 Pro** — hybrid reasoning, 1M context. Now fully stable for multi-turn agentic work.
- ✅ **Multi-turn fixed:** `@ai-sdk/deepseek@2.0.30` (released 2026-04-29) includes proper `reasoning_content` preservation and empty-string back-filling for V4 Pro in multi-turn requests with tool calls.
- ✅ **Works as orchestrator** — serves as our primary orchestrator in the custom preset.
- ✅ **Works as oracle** — deep reasoning with full tool-call support.
- **Provider:** `@ai-sdk/deepseek` (official dedicated provider, not `@ai-sdk/openai-compatible`).
- **Temperature:** Not set — V4 Pro thinking mode enforces its own optimal temperature.
- **Not recommended for:** (no restrictions — all previous limitations resolved).

---

## Scenario 1: Full Subscriptions (Z.ai + Kimi + DeepSeek) — Current

**Cost:** Z.ai Coding Plan + Kimi $39/mo + DeepSeek API (pay-per-token). OpenRouter for fallback/council only.
**Agent assignments:** `~/.config/opencode/oh-my-opencode-slim.json` (authoritative source — read the `custom` preset).

**Council:** GLM-5.1 (master) + Kimi K2.6 (R1) + Qwen 3.6 Plus (R2) + Claude Sonnet 4 (R3)

**Switching to this from another scenario:**
1. Set 2 agents (orchestrator, oracle) to `deepseek/deepseek-v4-pro` — no temperature
2. Set 2 agents (designer, fixer) to `kimi-for-coding/kimi-for-coding` — no temperature. Observer: `openrouter/~google/gemini-pro-latest`
3. Set 2 agents (explorer, librarian) to `zai-coding-plan/glm-5.1` with temps 0.3, 0.6
4. Restore fallback chains with subscription providers as first entries
5. Council custom: master=Z.ai, R1=Kimi, R2=Qwen, R3=Claude Sonnet

---

## Scenario 2: Z.ai Only (drop Kimi)

**Cost:** Z.ai Coding Plan only. OpenRouter for vision-dependent agents + fallback.
**Agent assignments:** `~/.config/opencode/oh-my-opencode-slim.json` (authoritative source).

**Key decisions:**
- **observer** → `openrouter/z-ai/glm-5v-turbo` (same lineage, vision, cheap on OR)
- **designer** → `openrouter/google/gemini-3-flash-preview` (multimodal, creative, cheap)
  - Alternative: `openrouter/moonshotai/kimi-k2.6` (better Visual QA, slightly more expensive)
- **fixer** → moves from Kimi to `zai-coding-plan/glm-5.1` (no vision needed, stays on subscription)
- OpenRouter costs only triggered for observer + designer calls (~30% of total tokens)

**Council:** GLM-5.1 (master) + DeepSeek V3.2 (R1) + Qwen 3.6 Plus (R2) + Claude Sonnet 4 (R3)

**Switching to this from Scenario 1:**
1. Change 3 agents: fixer → `zai-coding-plan/glm-5.1` (temp 0.1), designer → `openrouter/google/gemini-3-flash-preview` (temp 0.5), observer → `openrouter/z-ai/glm-5v-turbo` (temp 0.1)
2. Remove `kimi-for-coding/` from all fallback chains
3. Council custom: replace Kimi R1 with DeepSeek or Qwen
4. Optional: remove `kimi-for-coding` provider from `opencode.json`

---

## Scenario 3: Kimi Only (drop Z.ai)

**Cost:** Kimi $39/mo only. OpenRouter for fallback.
**Agent assignments:** `~/.config/opencode/oh-my-opencode-slim.json` (authoritative source).

**Trade-offs:**
- ✅ Single subscription, all multimodal, 262K context
- ❌ No model diversity (same model for all 7 agents)
- ❌ Temperature locked at 0.6 (high for fixer/explorer — less deterministic)
- ❌ Delegation diversity lost — orchestrator delegates to same model
- ❌ Kimi loop vulnerability with no fallback to different training lineage

**Not recommended** — the lack of model diversity defeats the purpose of multi-agent delegation. Use Scenario 2 instead if dropping one subscription.

---

## Vision Requirement Summary

Only two agents **require** multimodal input:

| Agent | Why vision matters | Impact if text-only |
|-------|--------------------|-------------------|
| **observer** | Reads images, PDFs, screenshots, video | Cannot fulfill its primary purpose |
| **designer** | Analyzes UI screenshots, mockups | Significant degradation |

All other agents (orchestrator, oracle, explorer, librarian, fixer) are text-only and work fine on any text model.

## Fallback Chain Pattern

Regardless of scenario, chains follow this structure:

```
primary (subscription or best available)
  → quality fallback 1 (different provider)
    → quality fallback 2
      → ...
        → free safety net (openrouter/qwen/qwen3-coder:free)
```

When switching scenarios, update chain first entries to match the new primary. The rest of the chain stays the same (openrouter quality gradient + free tail).

**Important:** Never leave the primary model as the first entry in its own fallback chain — it's a redundant retry on the same endpoint. When swapping the primary, also update the chain.

---

## Orchestrator Variants (Within Scenario 1)

Both subscriptions active, but orchestrator model can be swapped without changing anything else. This is the most common switch — evaluate which model handles delegation better.

### Variant A: Kimi Orchestrator (current)

```
orchestrator → Kimi K2.6 (thinking ON, temp 1.0 enforced)
fallback chain: GLM-5.1 → OR/GLM → Anthropic → OR/DeepSeek → OR/Qwen:free
```

4 Kimi agents (orchestrator, designer, fixer, observer) + 3 GLM agents (oracle, explorer, librarian).

### Variant B: GLM Orchestrator

```
orchestrator → GLM-5.1 (temp 0.3)
fallback chain: Kimi K2.6 → OR/GLM → Anthropic → OR/DeepSeek → OR/Qwen:free
```

4 GLM agents (orchestrator, oracle, explorer, librarian) + 3 Kimi agents (designer, fixer, observer).

---

## Quick Switch: Orchestrator Kimi → GLM

Edit `oh-my-opencode-slim.json` in both live and repo. **4 edits total (2 per file):**

**Edit 1** — Custom preset orchestrator (both files):

```diff
 "orchestrator": {
-  "model": "kimi-for-coding/kimi-for-coding",
+  "model": "zai-coding-plan/glm-5.1",
   "variant": "high",
+  "temperature": 0.3,
   "skills": ["*"],
   "mcps": ["web-search-prime"]
 }
```

Add `temperature: 0.3` (GLM respects it). Kimi had no temperature (enforced 0.6).

**Edit 2** — Live fallback chain only (repo chain has no subscription providers):

```diff
 "orchestrator": [
-  "zai-coding-plan/glm-5.1",
+  "kimi-for-coding/kimi-for-coding",
   "openrouter/z-ai/glm-5.1",
   "anthropic/claude-sonnet-4-6",
   "openrouter/deepseek/deepseek-v3.2",
   "openrouter/qwen/qwen3-coder:free"
 ]
```

Move Kimi to chain start (it's no longer the primary). Remove old GLM entry (now the primary, redundant).

**Verify:** `oc --doctor`

**Commit:** `git commit -m "switch: orchestrator → GLM-5.1"`

---

## Quick Switch: Orchestrator GLM → Kimi

Edit `oh-my-opencode-slim.json` in both live and repo. **4 edits total (2 per file):**

**Edit 1** — Custom preset orchestrator (both files):

```diff
 "orchestrator": {
-  "model": "zai-coding-plan/glm-5.1",
+  "model": "kimi-for-coding/kimi-for-coding",
   "variant": "high",
-  "temperature": 0.3,
   "skills": ["*"],
   "mcps": ["web-search-prime"]
 }
```

Remove `temperature` (Kimi enforces 0.6, setting it is misleading dead config).

**Edit 2** — Live fallback chain only (repo chain has no subscription providers):

```diff
 "orchestrator": [
-  "kimi-for-coding/kimi-for-coding",
+  "zai-coding-plan/glm-5.1",
   "openrouter/z-ai/glm-5.1",
   "anthropic/claude-sonnet-4-6",
   "openrouter/deepseek/deepseek-v3.2",
   "openrouter/qwen/qwen3-coder:free"
 ]
```

Move GLM to chain start (it's no longer the primary). Remove old Kimi entry (now the primary, redundant).

**Verify:** `oc --doctor`

**Commit:** `git commit -m "switch: orchestrator → Kimi K2.6"`

---

## Notes

- **Council is unaffected** by orchestrator swaps. Council master stays GLM-5.1, reviewer-1 stays Kimi K2.6 — regardless of which model runs the orchestrator.
- **Repo fallback chains** never include subscription providers — they use openrouter equivalents only. So the repo only needs the orchestrator model edit, not the fallback chain edit.
- **Temperature rule:** GLM agents get explicit temps. Kimi agents omit temp — API enforces 1.0 (thinking ON) or 0.6 (thinking OFF). Client-side temperature is ignored. Never set temperature on a Kimi agent — it's dead config that misleads future editors.
- **Thinking rule:**
  - **Kimi agents:** Must have `options: { thinking: { type: "enabled", budgetTokens: 16000 } }` in omo-slim. Model ID `kimi-for-coding` doesn't match OpenCode's auto-thinking patterns.
  - **GLM agents:** Thinking is auto-enabled by OpenCode (`transform.ts` detects "zai" in providerID). Do NOT add thinking options — they won't work due to a namespace mismatch between OpenCode (`zai-coding-plan` key) and `@ai-sdk/openai-compatible` SDK (`openaiCompatible` key). The auto-detection is the only working mechanism.
- **Fallback chain rule:** Remove the primary model from its own chain to avoid redundant same-endpoint retries.

## Related
- [[occams-code-setup]] — Architecture, config files, scripts
- [[agent-roles-and-models]] — Per-agent rationale, temperature strategy, MCP allocation
- [[troubleshooting]] — What to do when models fail
