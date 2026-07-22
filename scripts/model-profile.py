#!/usr/bin/env python3
"""Generate oh-my-opencode-slim.json from a concise model-profile.jsonc.

Usage:
  python3 model-profile.py model-profile.jsonc > oh-my-opencode-slim.json

The model-profile.jsonc specifies only the variable parts (model, temperature,
variant). Everything else (skills, MCPs, fallback chains, council reviewer
presets, infrastructure keys) is templated from constants.

Per-project overrides: use .opencode/oh-my-opencode-slim.jsonc
(the plugin already reads this and deep-merges at startup).

Why this exists:
  - Most of the generated config is repetitive boilerplate
  - Editing 8 presets × 8 role entries by hand is error-prone
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
        "mcps": ["context7", "gh_grep"],
    },
    "librarian": {
        "variant": "high",
        "skills": [],
        "mcps": ["web-search-prime", "websearch", "context7", "gh_grep"],
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
        "openai/gpt-5.6-sol",
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
        "openrouter/moonshotai/kimi-k3",
        "openrouter/google/gemini-3.5-flash",
        "anthropic/claude-sonnet-4-6",
        "openrouter/qwen/qwen3-coder:free",
    ],
    "observer": [
        "openrouter/moonshotai/kimi-k3",
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
        "zai-coding-plan/glm-5.2",
        "openai/gpt-5.6-terra",
        "deepseek/deepseek-v4-pro",
        "openrouter/google/gemini-3.5-flash",
    ],
    "fixer": [
        "kimi-for-coding/kimi-k3-1m",
        "deepseek/deepseek-v4-pro",
        "openrouter/deepseek/deepseek-v4-pro",
        "openrouter/qwen/qwen3-coder:free",
    ],

}


PRESET_ROLE_PREFIXES: dict[str, dict[str, list[str | dict[str, str]]]] = {
    "openai": {
        "orchestrator": ["zai-coding-plan/glm-5.2"],
        "oracle": ["zai-coding-plan/glm-5.2"],
        "librarian": ["zai-coding-plan/glm-5.2"],
        "explorer": ["zai-coding-plan/glm-5.2"],
        "fixer": ["zai-coding-plan/glm-5.2"],
        "council": [
            "zai-coding-plan/glm-5.2",
            "deepseek/deepseek-v4-pro",
        ],
    },
    "openai-fast": {
        "orchestrator": ["zai-coding-plan/glm-5.2"],
        "oracle": ["zai-coding-plan/glm-5.2"],
        "librarian": ["zai-coding-plan/glm-5.2"],
        "explorer": ["zai-coding-plan/glm-5.2"],
        "fixer": ["zai-coding-plan/glm-5.2"],
        "council": [
            "zai-coding-plan/glm-5.2",
            "deepseek/deepseek-v4-pro",
        ],
    },
    "custom": {
        "orchestrator": [{"id": "openai/gpt-5.6-sol", "variant": "xhigh"}],
        "librarian": [{"id": "openai/gpt-5.6-terra", "variant": "xhigh"}],
        "fixer": [{"id": "openai/gpt-5.6-sol", "variant": "xhigh"}],
    },
    "kimi": {
        "orchestrator": ["openai/gpt-5.6-sol-fast-high"],
    },
}


# ─── Council templates ─────────────────────────────────────────────────

COUNCIL_PRESETS: dict[str, dict[str, dict[str, Any]]] = {
    "custom": {
        "reviewer-1": {"model": "zai-coding-plan/glm-5.2", "variant": "max"},
        "reviewer-2": {"model": "openai/gpt-5.6-sol", "variant": "xhigh"},
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
        "reviewer-1": {"model": "kimi-for-coding/kimi-k3-1m"},
        "reviewer-2": {"model": "openrouter/deepseek/deepseek-v4-pro"},
        "reviewer-3": {"model": "openrouter/anthropic/claude-sonnet-4.6"},
    },
    "openai": {
        "reviewer-1": {"model": "zai-coding-plan/glm-5.2", "variant": "max"},
        "reviewer-2": {"model": "openrouter/anthropic/claude-sonnet-4.6", "variant": "high"},
        "reviewer-3": {"model": "deepseek/deepseek-v4-pro", "variant": "max"},
    },
    "kimi": {
        "reviewer-1": {"model": "kimi-for-coding/kimi-k3-1m"},
        "reviewer-2": {"model": "openai/gpt-5.5-fast", "variant": "xhigh"},
        "reviewer-3": {"model": "deepseek/deepseek-v4-pro", "variant": "max"},
    },
}


# ─── Build logic ────────────────────────────────────────────────────────

OPENROUTER_ONLY_PRESETS = {"balanced", "cheap"}

OPENAI_FAST_MODEL_ALIASES = {
    "openai/gpt-5.6-sol": "openai/gpt-5.6-sol-fast",
    "openai/gpt-5.6-terra": "openai/gpt-5.6-terra-fast",
    "openai/gpt-5.6-luna": "openai/gpt-5.6-luna-fast",
    "openai/gpt-5.5": "openai/gpt-5.5-fast",
}

KIMI_COUNCIL_MODEL_ALIASES = dict(OPENAI_FAST_MODEL_ALIASES)

COUNCIL_MODEL_ALIASES_BY_PRESET = {
    "openai-fast": OPENAI_FAST_MODEL_ALIASES,
    "kimi": KIMI_COUNCIL_MODEL_ALIASES,
}

FAST_MODEL_DEDUPE_EQUIVALENCE = {
    fast: base for base, fast in OPENAI_FAST_MODEL_ALIASES.items()
}


def model_id(model: str | dict[str, Any]) -> str:
    """Return the provider/model ID from a string or per-model config object."""
    return model["id"] if isinstance(model, dict) else model


def map_model_refs(value: Any, aliases: dict[str, str] | None) -> Any:
    """Map exact model references recursively while preserving structure."""
    if isinstance(value, str):
        return (aliases or {}).get(value, value)
    if isinstance(value, list):
        return [map_model_refs(item, aliases) for item in value]
    if isinstance(value, dict):
        return {key: map_model_refs(item, aliases) for key, item in value.items()}
    return value


def build_agent_config(agent_name: str, override: dict[str, Any],
                       fallback_chains: dict[str, list[str]] | None = None,
                       *, fallback_prefix: list[str | dict[str, str]] | None = None,
                       openrouter_only: bool = False,
                       model_aliases: dict[str, str] | None = None) -> dict[str, Any]:
    """Merge per-agent defaults with preset-specific overrides.

    Rules:
      - model: primary, preset-role prefix, then global role chain with stable
        ID-based de-duplication
      - variant: non-null override > default; explicit null omits the field
      - temperature: emitted when present in the override
      - skills/mcps: from defaults (override can't change these)
      - model-specific options: not injected; they live in opencode.json
    """
    defaults = AGENT_DEFAULTS.get(agent_name, {})
    config: dict[str, Any] = {}

    # Build model array for the v2.0.4+ fallback mechanism.
    chains = fallback_chains or {}
    candidates: list[str | dict[str, Any]] = [
        override["model"],
        *(fallback_prefix or []),
        *chains.get(agent_name, []),
    ]
    candidates = [map_model_refs(model, model_aliases) for model in candidates]
    primary = candidates[0]
    if openrouter_only:
        candidates = [model for model in candidates if model_id(model).startswith("openrouter/")]

    model_array: list[str | dict[str, Any]] = []
    seen_model_ids: set[str] = set()
    for model in candidates:
        identifier = model_id(model)
        dedupe_key = FAST_MODEL_DEDUPE_EQUIVALENCE.get(identifier, identifier)
        if dedupe_key in seen_model_ids:
            continue
        seen_model_ids.add(dedupe_key)
        model_array.append(model)

    config["model"] = model_array if len(model_array) > 1 else primary

    # Variant (defaults only exist for explorer/librarian/fixer/observer)
    # OpenCode silently ignores variants for models that don't support them
    # (transform.variants() returns {} → variant lookup yields undefined).
    # So it's safe and portable to always include the variant — if you later
    # switch to a model that supports variants, it Just Works.
    if "variant" in override:
        if override["variant"] is not None:
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
            preset_agents[agent_name] = build_agent_config(
                agent_name,
                agent_cfg,
                fallback_chains,
                fallback_prefix=PRESET_ROLE_PREFIXES.get(preset_name, {}).get(agent_name),
                openrouter_only=preset_name in OPENROUTER_ONLY_PRESETS,
                model_aliases=(
                    OPENAI_FAST_MODEL_ALIASES
                    if preset_name in {"openai-fast", "kimi"}
                    else None
                ),
            )
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

    def _filter_reviewer(
        raw: dict[str, Any], model_aliases: dict[str, str] | None = None
    ) -> dict[str, Any]:
        reviewer = {k: v for k, v in raw.items() if k in REVIEWER_KEYS}
        if model_aliases and "model" in reviewer:
            reviewer["model"] = map_model_refs(reviewer["model"], model_aliases)
        return reviewer

    # Start from hardcoded defaults
    result: dict[str, Any] = {
        "default_preset": active_preset,
        "presets": {name: {k: _filter_reviewer(
                                r, COUNCIL_MODEL_ALIASES_BY_PRESET.get(name))
                             for k, r in preset.items()}
                    for name, preset in COUNCIL_PRESETS.items()},
    }

    # Override from jsonc input
    if council_map:
        if "default_preset" in council_map:
            result["default_preset"] = council_map["default_preset"]
        if "presets" in council_map:
            for preset_name, reviewers in council_map["presets"].items():
                result["presets"][preset_name] = {
                    k: _filter_reviewer(
                        r, COUNCIL_MODEL_ALIASES_BY_PRESET.get(preset_name)
                    )
                    for k, r in reviewers.items()
                }

    return result


def build_full_config(model_map: dict[str, Any]) -> dict[str, Any]:
    """Generate the complete oh-my-opencode-slim.json from model-map input."""
    return {
        "$schema": "https://unpkg.com/oh-my-opencode-slim@2.2.7/oh-my-opencode-slim.schema.json",
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
            # and retry_on_empty are actively used by v2.0.4+ runtime.
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
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
