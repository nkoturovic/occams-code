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
  - Most of the generated config is repetitive boilerplate
  - Editing 6 presets × 8 role entries by hand is error-prone
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
    # Max 4 per chain — diverse providers, lean set
    "orchestrator": [
        "deepseek/deepseek-v4-pro",
        "openai/gpt-5.5",
        "openrouter/deepseek/deepseek-v4-pro",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "oracle": [
        "deepseek/deepseek-v4-pro",
        "anthropic/claude-opus-4-7",
        "openrouter/deepseek/deepseek-v4-pro",
        "openrouter/anthropic/claude-sonnet-4.6",
    ],
    "designer": [
        "openrouter/moonshotai/kimi-k2.7-code",
        "openrouter/google/gemini-3.5-flash",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "observer": [
        "openrouter/moonshotai/kimi-k2.7-code",
        "openrouter/google/gemini-3.5-flash",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "explorer": [
        "zai-coding-plan/glm-5.2",
        "openrouter/google/gemini-3.5-flash",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "librarian": [
        "deepseek/deepseek-v4-pro",
        "openrouter/google/gemini-3.5-flash",
        "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "fixer": [
        "kimi-for-coding/kimi-for-coding",
        "deepseek/deepseek-v4-pro",
        "openrouter/deepseek/deepseek-v4-pro",
        "openrouter/qwen/qwen3-coder:free",
    ],

}


# ─── Council templates ─────────────────────────────────────────────────

COUNCIL_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "custom": {
        "reviewer-1": {"model": "zai-coding-plan/glm-5.2", "variant": "max"},
        "reviewer-2": {"model": "openai/gpt-5.5", "variant": "xhigh"},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
    "balanced": {
        "reviewer-1": {"model": "openrouter/deepseek/deepseek-v4-pro"},
        "reviewer-2": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
    "cheap": {
        "reviewer-1": {"model": "openrouter/qwen/qwen3-coder:free"},
        "reviewer-2": {"model": "openrouter/nvidia/nemotron-3-super-120b-a12b:free"},
    },
    "premium": {
        "reviewer-1": {"model": "anthropic/claude-sonnet-4-6"},
        "reviewer-2": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
        "reviewer-3": {"model": "openrouter/google/gemini-3.5-flash"},
    },
    "deepseek": {
        "reviewer-1": {"model": "kimi-for-coding/kimi-for-coding"},
        "reviewer-2": {"model": "openrouter/deepseek/deepseek-v4-pro"},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
    "openai": {
        "reviewer-1": {"model": "zai-coding-plan/glm-5.2", "variant": "max"},
        "reviewer-2": {"model": "openrouter/anthropic/claude-sonnet-4.6", "variant": "high"},
        "reviewer-3": {"model": "deepseek/deepseek-v4-pro", "variant": "max"},
    },
}


# ─── Build logic ────────────────────────────────────────────────────────

def build_agent_config(agent_name: str, override: dict[str, Any],
                       fallback_chains: dict[str, list[str]] | None = None) -> dict[str, Any]:
    """Merge per-agent defaults with preset-specific overrides.

    Rules:
      - model: always from override (required); merged with fallback chain
        into an array for v2.0.4+ model-array fallback mechanism
      - variant: override > default (orchestrator/designer have no default variant)
      - temperature: from override; absent if model uses thinking mode
      - skills/mcps: from defaults (override can't change these)
      - options.thinking: auto-injected for kimi-for-coding models;
        removed for deepseek-v4-pro (dedicated provider handles it);
        NOT injected for any other model.
    """
    defaults = AGENT_DEFAULTS.get(agent_name, {})
    config: dict[str, Any] = {}

    # Build model: primary + fallback chain as array (v2.0.4+ mechanism)
    primary = override["model"]
    chains = fallback_chains or {}
    chain = chains.get(agent_name, [])
    model_array = [primary] + [m for m in chain if m != primary]
    config["model"] = model_array if len(model_array) > 1 else primary

    # Use primary model string for type detection
    model = primary

    # Variant (defaults only exist for explorer/librarian/fixer/observer)
    # OpenCode silently ignores variants for models that don't support them
    # (transform.variants() returns {} → variant lookup yields undefined).
    # So it's safe and portable to always include the variant — if you later
    # switch to a model that supports variants, it Just Works.
    if "variant" in override:
        config["variant"] = override["variant"]
    elif "variant" in defaults:
        config["variant"] = defaults["variant"]
    else:
        config["variant"] = "high"

    # Skills and MCPs (from defaults, override can't change these)
    config["skills"] = defaults.get("skills", [])
    config["mcps"] = defaults.get("mcps", [])

    # NOTE: Per-model options (thinking, reasoningEffort) are NOT injected here.
    # They live in the model definitions in opencode.json, which are model-specific
    # and don't leak to fallback models when model-array fallback triggers.
    # The variant system (model variant overrides) also lives in opencode.json.
    # This prevents the C3 issue where primary-model options would be sent to
    # fallback models that don't support them.

    # Temperature applies to ALL models (including thinking-mode ones)
    if "temperature" in override:
        config["temperature"] = override["temperature"]

    return config


def build_presets(preset_map: dict[str, dict[str, Any]],
                  fallback_chains: dict[str, list[str]] | None = None) -> dict[str, dict[str, Any]]:
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
            preset_agents[agent_name] = build_agent_config(agent_name, agent_cfg, fallback_chains)
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
        "backgroundJobs": model_map.get("backgroundJobs", {
            "maxSessionsPerAgent": 2,
            "readContextMinLines": 10,
            "readContextMaxFiles": 8,
        }),
        "presets": build_presets(
            model_map.get("presets", {}),
            model_map.get("fallback_chains", FALLBACK_CHAINS),
        ),
        "fallback": {
            "enabled": True,
            # NOTE: timeoutMs/retryDelayMs are schema-valid but only enabled
            # and retry_on_empty are actively used by v2.0.4 runtime.
            "timeoutMs": 60000,
            "retryDelayMs": 500,
            "retry_on_empty": True,
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
