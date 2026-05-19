#!/usr/bin/env python3
"""Generate oh-my-opencode-slim.json from a concise model-profile.jsonc.

Usage:
  python3 model-profile.py model-profile.jsonc > oh-my-opencode-slim.json

The model-profile.jsonc specifies only the variable parts (model, temperature,
variant, thinking options). Everything else (skills, MCPs, fallback chains,
council reviewer presets, infrastructure keys) is templated from constants.

Per-project overrides: use .opencode/oh-my-opencode-slim.jsonc
(the plugin already reads this and deep-merges at startup).

Why this exists:
  - 61% of the 457-line config is repetitive boilerplate
  - Editing 4 presets × 7 agents by hand is error-prone
  - When models change, you update one mapping file, regenerate, deploy

Design (Occam's Code):
  - Zero dependencies (Python stdlib only)
  - JSONC input with comments
  - Agent role defaults embedded as constants
  - Single-file script, single-file input → single-file output
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


# ─── JSONC parsing (no deps) ───────────────────────────────────────────

def strip_jsonc(text: str) -> str:
    """Strip // and /* */ comments from JSONC, handle strings safely."""
    pattern = re.compile(
        r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`'
        r'|//.*?$|/\*[\s\S]*?\*/',
        re.MULTILINE,
    )

    def _replace(m: re.Match[str]) -> str:
        token = m.group(0)
        if token.startswith("/"):
            return " "  # replace comments with space (preserve line lengths for error messages)
        return token

    return pattern.sub(_replace, text)


def parse_jsonc(path: Path) -> dict[str, Any]:
    """Read and parse a JSONC file."""
    text = path.read_text(encoding="utf-8")
    stripped = strip_jsonc(text)
    return json.loads(stripped)


# ─── Agent role defaults (skills, MCPs — identical across all presets) ─

AGENT_DEFAULTS: dict[str, dict[str, Any]] = {
    "orchestrator": {
        "skills": ["*"],
        "mcps": ["web-search-prime", "websearch"],
    },
    "oracle": {
        "skills": [],
        "mcps": ["web-search-prime", "websearch", "context7"],
    },
    "designer": {
        "skills": ["agent-browser"],
        "mcps": ["web-search-prime", "websearch", "context7", "zai_vision"],
    },
    "explorer": {
        "variant": "high",
        "skills": [],
        "mcps": ["context7", "grep_app"],
    },
    "librarian": {
        "variant": "high",
        "skills": [],
        "mcps": ["web-search-prime", "websearch", "context7", "grep_app"],
    },
    "fixer": {
        "variant": "high",
        "skills": [],
        "mcps": ["context7"],
    },
    "observer": {
        "variant": "high",
        "skills": ["video-analysis", "lecture-notes", "audio-analysis"],
        "mcps": ["zai_vision"],
    },

}


# ─── Fallback chain templates ──────────────────────────────────────────

FALLBACK_CHAINS: dict[str, list[str]] = {
    "orchestrator": [
        "deepseek/deepseek-v4-pro",
        "zai-coding-plan/glm-5.1",
        "openrouter/z-ai/glm-5.1",
        "anthropic/claude-sonnet-4-6",
        "openrouter/deepseek/deepseek-v3.2",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "oracle": [
        "openrouter/deepseek/deepseek-v3.2",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3.6-plus",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "designer": [
        "kimi-for-coding/kimi-for-coding",
        "openrouter/moonshotai/kimi-k2.6",
        "openrouter/google/gemini-3.1-pro-preview",
        "openrouter/google/gemini-3-flash-preview",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "observer": [
        "openrouter/moonshotai/kimi-k2.6",
        "kimi-for-coding/kimi-for-coding",
        "openrouter/z-ai/glm-5v-turbo",
        "anthropic/claude-sonnet-4-6",
        "openrouter/google/gemini-3-flash-preview",
    ],
    "explorer": [
        "openrouter/deepseek/deepseek-v3.2",
        "openrouter/qwen/qwen3.6-plus",
        "openrouter/google/gemini-3-flash-preview",
        "openrouter/qwen/qwen3-coder",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    ],
    "librarian": [
        "openrouter/qwen/qwen3.6-plus",
        "openrouter/deepseek/deepseek-v3.2",
        "openrouter/google/gemini-3-flash-preview",
        "openrouter/qwen/qwen3-coder",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    ],
    "fixer": [
        "kimi-for-coding/kimi-for-coding",
        "zai-coding-plan/glm-5.1",
        "openrouter/deepseek/deepseek-v3.2",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
    ],

}


# ─── Council templates ─────────────────────────────────────────────────

COUNCIL_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "custom": {
        "reviewer-1": {"model": "kimi-for-coding/kimi-for-coding"},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus"},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
    "balanced": {
        "reviewer-1": {"model": "openrouter/z-ai/glm-5.1"},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus"},
    },
    "cheap": {
        "reviewer-1": {"model": "openrouter/qwen/qwen3-coder"},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus"},
        "reviewer-3": {"model": "openrouter/nvidia/nemotron-3-super-120b-a12b:free"},
    },
    "premium": {
        "reviewer-1": {"model": "anthropic/claude-sonnet-4-6"},
        "reviewer-2": {"model": "openrouter/z-ai/glm-5.1"},
        "reviewer-3": {"model": "openrouter/google/gemini-3.1-pro-preview"},
    },
    "deepseek": {
        "reviewer-1": {"model": "kimi-for-coding/kimi-for-coding"},
        "reviewer-2": {"model": "openrouter/z-ai/glm-5.1"},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
}


# ─── Build logic ────────────────────────────────────────────────────────

def build_agent_config(agent_name: str, override: dict[str, Any]) -> dict[str, Any]:
    """Merge per-agent defaults with preset-specific overrides.

    Rules:
      - model: always from override (required)
      - variant: override > default (orchestrator/designer have no default variant)
      - temperature: from override; absent if model uses thinking mode
      - skills/mcps: from defaults (override can't change these)
      - options.thinking: auto-injected for kimi-for-coding models;
        removed for deepseek-v4-pro (dedicated provider handles it);
        NOT injected for any other model.
    """
    defaults = AGENT_DEFAULTS.get(agent_name, {})
    config: dict[str, Any] = {}

    # Required fields
    config["model"] = override["model"]

    # Variant (defaults only exist for explorer/librarian/fixer/observer)
    variant = override.get("variant", defaults.get("variant", "high"))
    config["variant"] = variant

    # Skills and MCPs (from defaults, override can't change these)
    config["skills"] = defaults.get("skills", [])
    config["mcps"] = defaults.get("mcps", [])

    # Temperature — always from override if set (including thinking-mode models)
    model = config["model"]
    is_kimi = "kimi-for-coding" in model
    is_deepseek_v4 = "deepseek-v4-pro" in model
    is_glm_zai = "zai-coding-plan/glm" in model
    is_gemini = "gemini" in model

    if is_kimi:
        # Kimi agents use thinking options
        budget = override.get("thinking", 16000)
        config["options"] = {
            "thinking": {"type": "enabled", "budgetTokens": budget}
        }
    elif is_gemini:
        # Gemini through OpenRouter (@ai-sdk/openai-compatible):
        # variant system auto-generates {reasoningEffort: "high"} from the
        # "high" variant — the maximum available. No manual options needed.
        # Any reasoningEffort set here would be overridden by the variant anyway.
        pass
    elif is_deepseek_v4:
        # DeepSeek V4 Pro — no special options needed
        pass
    elif is_glm_zai:
        # GLM 5.1 — explicit thinking config matching model options
        effort = override.get("reasoningEffort", "max")
        config["options"] = {
            "thinking": {"type": "enabled", "clear_thinking": False},
            "reasoningEffort": effort
        }

    # Temperature applies to ALL models (including thinking-mode ones)
    if "temperature" in override:
        config["temperature"] = override["temperature"]

    return config


def build_presets(preset_map: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build the full presets section from the input map.

    Input:
      { "custom": { "orchestrator": {"model": "...", ...}, ... }, ... }

    Output:
      { "cheap": { "orchestrator": {...}, ... }, ... }
    """
    presets: dict[str, dict[str, Any]] = {}

    for preset_name, agents in preset_map.items():
        preset_agents: dict[str, Any] = {}
        for agent_name, agent_cfg in agents.items():
            preset_agents[agent_name] = build_agent_config(agent_name, agent_cfg)
        presets[preset_name] = preset_agents

    return presets


def build_council(council_map: dict[str, Any] | None, active_preset: str = "custom") -> dict[str, Any]:
    """Build council config from hardcoded defaults, with optional jsonc overrides.

    Merge strategy: if jsonc has a ``council`` key, its presets replace
    individual hardcoded entries by name.  Unspecified presets fall back
    to COUNCIL_PRESETS.  ``default_preset`` is auto-derived from the
    top-level ``preset`` field unless explicitly set in the jsonc.

    Only {model, variant, prompt} keys are emitted per reviewer — any
    extra keys (temperature, options, thinking) are stripped defensively.
    """
    # Allowed keys per reviewer (omo-slim CouncillorConfigSchema)
    REVIEWER_KEYS = {"model", "variant", "prompt"}

    def _filter_reviewer(raw: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in raw.items() if k in REVIEWER_KEYS}

    # Start from hardcoded defaults
    result: dict[str, Any] = {
        "default_preset": active_preset,
        "councillor_execution_mode": "parallel",
        "presets": {name: {k: _filter_reviewer(r) for k, r in preset.items()}
                    for name, preset in COUNCIL_PRESETS.items()},
    }

    # Override from jsonc input
    if council_map:
        if "default_preset" in council_map:
            result["default_preset"] = council_map["default_preset"]
        if "councillor_execution_mode" in council_map:
            result["councillor_execution_mode"] = council_map["councillor_execution_mode"]
        if "presets" in council_map:
            for preset_name, reviewers in council_map["presets"].items():
                result["presets"][preset_name] = {
                    k: _filter_reviewer(r) for k, r in reviewers.items()
                }

    return result


def build_full_config(model_map: dict[str, Any]) -> dict[str, Any]:
    """Generate the complete oh-my-opencode-slim.json from model-map input."""
    return {
        "$schema": "https://unpkg.com/oh-my-opencode-slim@latest/oh-my-opencode-slim.schema.json",
        "preset": model_map.get("preset", "custom"),
        "disabled_agents": model_map.get("disabled_agents", []),
        "multiplexer": model_map.get("multiplexer", {"type": "none"}),
        "todoContinuation": model_map.get("todoContinuation", {
            "maxContinuations": 15,
            "cooldownMs": 5000,
            "autoEnable": False,
            "autoEnableThreshold": 4,
        }),
        "presets": build_presets(model_map.get("presets", {})),
        "fallback": {
            "enabled": True,
            "timeoutMs": 60000,
            "chains": model_map.get("fallback_chains", FALLBACK_CHAINS),
        },
        "council": build_council(model_map.get("council"), model_map.get("preset", "custom")),
    }


# ─── Main ───────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python3 model-profile.py model-profile.jsonc [output.json]", file=sys.stderr)
        print("  Reads model-profile.jsonc, writes oh-my-opencode-slim.json", file=sys.stderr)
        return 1

    map_path = Path(sys.argv[1])
    if not map_path.exists():
        print(f"Error: {map_path} not found", file=sys.stderr)
        return 1

    model_map = parse_jsonc(map_path)
    config = build_full_config(model_map)

    output = json.dumps(config, indent=2, ensure_ascii=False) + "\n"

    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(output, encoding="utf-8")
        print(f"✓ Generated {sys.argv[2]}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
