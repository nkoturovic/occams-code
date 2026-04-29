#!/usr/bin/env python3
"""Generate oh-my-opencode-slim.json from a concise model-profile.jsonc.

Usage:
  python3 model-profile.py model-profile.jsonc > oh-my-opencode-slim.json

The model-profile.jsonc specifies only the variable parts (model, temperature,
variant, thinking options). Everything else (skills, MCPs, fallback chains,
council config, infrastructure keys) is templated from constants.

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
        "mcps": ["web-search-prime"],
    },
    "oracle": {
        "skills": [],
        "mcps": ["web-search-prime", "context7"],
    },
    "designer": {
        "skills": ["agent-browser"],
        "mcps": ["web-search-prime", "context7", "zai_vision"],
    },
    "explorer": {
        "variant": "high",
        "skills": [],
        "mcps": ["context7", "grep_app"],
    },
    "librarian": {
        "variant": "high",
        "skills": [],
        "mcps": ["web-search-prime", "context7", "grep_app"],
    },
    "fixer": {
        "variant": "high",
        "skills": [],
        "mcps": ["context7"],
    },
    "observer": {
        "variant": "high",
        "skills": [],
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
        "deepseek/deepseek-v3.2",
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
        "kimi-for-coding/kimi-for-coding",
        "openrouter/moonshotai/kimi-k2.6",
        "openrouter/z-ai/glm-5v-turbo",
        "openrouter/google/gemini-3.1-pro-preview",
        "openrouter/google/gemini-3-flash-preview",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
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
        "master":     {"model": "zai-coding-plan/glm-5.1", "temperature": 0.6},
        "reviewer-1": {"model": "kimi-for-coding/kimi-for-coding", "temperature": 1.0},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus", "temperature": 0.6},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6", "temperature": 0.3},
    },
    "balanced": {
        "master":     {"model": "anthropic/claude-sonnet-4-6", "temperature": 0.3},
        "reviewer-1": {"model": "openrouter/z-ai/glm-5.1", "temperature": 1.0},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus", "temperature": 0.6},
    },
    "cheap": {
        "master":     {"model": "openrouter/deepseek/deepseek-v3.2", "temperature": 0.3},
        "reviewer-1": {"model": "openrouter/qwen/qwen3-coder", "temperature": 1.0},
        "reviewer-2": {"model": "openrouter/qwen/qwen3.6-plus", "temperature": 0.6},
        "reviewer-3": {"model": "openrouter/nvidia/nemotron-3-super-120b-a12b:free", "temperature": 1.0},
    },
    "premium": {
        "master":     {"model": "anthropic/claude-opus-4-6", "temperature": 0.3},
        "reviewer-1": {"model": "anthropic/claude-sonnet-4-6", "temperature": 0.6},
        "reviewer-2": {"model": "openrouter/z-ai/glm-5.1", "temperature": 1.0},
        "reviewer-3": {"model": "openrouter/google/gemini-3.1-pro-preview", "temperature": 1.0},
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

    # Temperature — explicitly set in override, or absent
    model = config["model"]
    is_kimi = "kimi-for-coding" in model
    is_deepseek_v4 = "deepseek-v4-pro" in model

    if is_kimi:
        # Kimi enforces temperature via API — never set it
        # Kimi agents use thinking options instead
        budget = override.get("thinking", 16000)
        config["options"] = {
            "thinking": {"type": "enabled", "budgetTokens": budget}
        }
    elif is_deepseek_v4:
        # DeepSeek V4 Pro thinking auto-handled by @ai-sdk/deepseek provider
        # No temperature (thinking mode enforces its own)
        # No options needed (provider handles it natively)
        pass
    else:
        # Other models: temperature from override
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
    agent_names = list(AGENT_DEFAULTS.keys())
    presets: dict[str, dict[str, Any]] = {}

    for preset_name, agents in preset_map.items():
        preset_agents: dict[str, Any] = {}
        for agent_name in agent_names:
            if agent_name not in agents:
                print(f"Warning: {preset_name}.{agent_name} missing from model-map, using defaults", file=sys.stderr)
                continue
            preset_agents[agent_name] = build_agent_config(agent_name, agents[agent_name])
        presets[preset_name] = preset_agents

    return presets


def build_council(council_map: dict[str, Any] | None) -> dict[str, Any]:
    """Build council config from template, with optional overrides from model-map."""
    if council_map:
        # Merge with defaults — only model/temp are overridable
        result = dict(council_map)
        # Ensure default_preset matches the active preset
        if "default_preset" not in result:
            result["default_preset"] = "custom"
        if "master" not in result:
            result["master"] = {"model": "zai-coding-plan/glm-5.1"}
        return result
    return {
        "master": {"model": "zai-coding-plan/glm-5.1"},
        "default_preset": "custom",
        "councillor_execution_mode": "parallel",
        "presets": COUNCIL_PRESETS,
    }


def build_full_config(model_map: dict[str, Any]) -> dict[str, Any]:
    """Generate the complete oh-my-opencode-slim.json from model-map input."""
    return {
        "preset": model_map.get("preset", "custom"),
        "disabled_agents": model_map.get("disabled_agents", []),
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
        "council": build_council(model_map.get("council")),
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
