#!/usr/bin/env python3
"""
OpenCode model configuration doctor.

Validates capability flags, referential integrity, API key presence,
output cap, and zombie config. Reads opencode.json and
oh-my-opencode-slim.json (core config + slim plugin config).

Usage:
    python3 doctor-model-check.py
    python3 doctor-model-check.py --core-config /path/to/opencode.json
    python3 doctor-model-check.py --quiet    # exit code only, no output

Exit codes:
    0 = all clear (includes warnings-only — they don't block)
    1 = critical errors found
"""

import json
import os
import sys
import argparse
import contextlib
import copy
import importlib.util
import io
import tempfile
from pathlib import Path

# ── ansi ────────────────────────────────────────────────────────────────
GREEN  = "\033[0;32m"
RED    = "\033[0;31m"
YELLOW = "\033[0;33m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── helpers ─────────────────────────────────────────────────────────────

def load_json(path_str: str) -> dict:
    """Load JSON, expanding ~ and raising clean errors."""
    p = Path(path_str).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    with open(p) as f:
        return json.load(f)


MAGENTA = "\033[0;35m"

def check(severity: str, label: str, predicate: bool, detail: str = "",
          errors: int = 0, warnings: int = 0) -> tuple[int, int]:
    """Print a single check result and bump the appropriate counter.

    CRITICAL → ✗ red, bumps errors (exit 1 on fail)
    HIGH     → ✗ magenta, bumps warnings (non-blocking)
    WARNING  → ⚠ yellow, bumps warnings (non-blocking)
    """
    if predicate:
        return errors, warnings
    if severity == "CRITICAL":
        print(f"  {RED}✗{RESET} [{severity}] {label}  {DIM}{detail}{RESET}")
        return errors + 1, warnings
    elif severity == "HIGH":
        print(f"  {MAGENTA}✗{RESET} [{severity}] {label}  {DIM}{detail}{RESET}")
        return errors, warnings + 1
    else:  # WARNING
        print(f"  {YELLOW}⚠{RESET} [{severity}] {label}  {DIM}{detail}{RESET}")
        return errors, warnings + 1


def iter_models(pv: dict) -> list[tuple[str, dict]]:
    """Safely iterate model entries from a provider dict.

    Guards against None, list, or missing 'models' key.
    """
    models = pv.get("models")
    if not isinstance(models, dict):
        return []
    return list(models.items())


def normalize_model_ref(
    value, path: str = "model", *, allow_object: bool = False
) -> tuple[list[str], list[tuple[str, str]]]:
    """Normalize model references and return precise validation errors."""
    if isinstance(value, str):
        if value.strip():
            return [value], []
        return [], [(path, "expected a non-empty model ID string")]

    if isinstance(value, dict):
        if not allow_object:
            return [], [(path, "expected a model string or non-empty array")]
        refs = []
        issues = []
        model_id = value.get("id")
        if isinstance(model_id, str) and model_id.strip():
            refs.append(model_id)
        else:
            issues.append((f"{path}.id", "expected a non-empty string"))
        if "variant" in value and not isinstance(value["variant"], str):
            issues.append((f"{path}.variant", "expected a string"))
        return refs, issues

    if isinstance(value, list):
        if allow_object:
            return [], [(path, "nested model arrays are not supported")]
        if not value:
            return [], [(path, "expected a non-empty model array")]
        refs = []
        issues = []
        for index, item in enumerate(value):
            item_refs, item_issues = normalize_model_ref(
                item, f"{path}[{index}]", allow_object=True
            )
            refs.extend(item_refs)
            issues.extend(item_issues)
        return refs, issues

    return [], [(
        path,
        f"expected a model string, object, or non-empty array; got {type(value).__name__}",
    )]

def check_temperature(core: dict) -> tuple[int, int]:
    """C1: temperature flag present on every custom-provider (npm) model.

    `temperature: true`  → exposed to the model (pass)
    `temperature: false` → intentional suppression (pass; e.g. Kimi K3)
    missing / None       → CRITICAL (plugin temperatures silently dropped)
    """
    errors = warnings = 0
    for pn, pv in core.get("provider", {}).items():
        if "npm" not in pv:
            continue
        for mn, mv in iter_models(pv):
            errors, warnings = check(
                "CRITICAL",
                f"Missing temperature flag on {pn}/{mn}",
                mv.get("temperature") is not None,
                "plugin temperatures silently dropped "
                "(set true, or false if intentionally suppressed)",
                errors, warnings,
            )
    return errors, warnings


def check_reasoning(core: dict) -> tuple[int, int]:
    """C2: reasoning:true on reasoning-capable custom-provider models."""
    errors = warnings = 0
    patterns = {"glm", "deepseek", "kimi", "gemini-3", "nemotron", "qwen3", "claude"}
    for pn, pv in core.get("provider", {}).items():
        if "npm" not in pv:
            continue
        for mn, mv in iter_models(pv):
            if any(p in mn.lower() for p in patterns):
                errors, warnings = check(
                    "WARNING",
                    f"Missing reasoning:true on {pn}/{mn}",
                    bool(mv.get("reasoning")),
                    "reasoning capability not exposed",
                    errors, warnings,
                )
    return errors, warnings


def collect_valid_models(core: dict) -> set[str]:
    """Build set of 'providerId/modelId' strings from opencode.json."""
    valid = set()
    for pn, pv in core.get("provider", {}).items():
        for mn, _mv in iter_models(pv):
            valid.add(f"{pn}/{mn}")
    return valid


def check_referential_integrity(core: dict, slim: dict) -> tuple[int, int]:
    """C3: every model reference in slim.json resolves to a defined model.

    Model references may be a string or a non-empty flat array containing
    strings and {id, variant?} objects. Every element must be valid and resolve.

    Note: `fallback.chains` was removed in v2.0.4. Fallback ordering is
    now expressed by the array order on each agent's `model` field.
    """
    errors = warnings = 0
    valid = collect_valid_models(core)

    # council presets
    for preset_name, preset in slim.get("council", {}).get("presets", {}).items():
        for role, entry in preset.items():
            model_path = f"council.{preset_name}.{role}.model"
            refs, issues = normalize_model_ref(
                entry.get("model") if isinstance(entry, dict) else None,
                model_path,
            )
            for path, detail in issues:
                errors, warnings = check(
                    "CRITICAL",
                    f"Malformed model reference: {path}",
                    False,
                    detail,
                    errors, warnings,
                )
            for mid in refs:
                errors, warnings = check(
                    "CRITICAL",
                    f"Broken reference: council.{preset_name}.{role} → {mid}",
                    mid in valid,
                    "model not defined in opencode.json",
                    errors, warnings,
                )

    # agent presets (model may be a string or array of fallback models)
    for preset_name, preset in slim.get("presets", {}).items():
        for agent_name, agent_cfg in preset.items():
            model_path = f"preset.{preset_name}.{agent_name}.model"
            refs, issues = normalize_model_ref(
                agent_cfg.get("model") if isinstance(agent_cfg, dict) else None,
                model_path,
            )
            for path, detail in issues:
                errors, warnings = check(
                    "CRITICAL",
                    f"Malformed model reference: {path}",
                    False,
                    detail,
                    errors, warnings,
                )
            for mid in refs:
                errors, warnings = check(
                    "CRITICAL",
                    f"Broken reference: preset.{preset_name}.{agent_name} → {mid}",
                    mid in valid,
                    "model not defined in opencode.json",
                    errors, warnings,
                )

    return errors, warnings


OPENAI_FAST_REFERENCE_EQUIVALENCE = {
    "openai/gpt-5.6-sol-fast": "openai/gpt-5.6-sol",
    "openai/gpt-5.6-terra-fast": "openai/gpt-5.6-terra",
    "openai/gpt-5.6-luna-fast": "openai/gpt-5.6-luna",
    "openai/gpt-5.5-fast": "openai/gpt-5.5",
}

OPENAI_FAST_SPEC = {
    "gpt-5.6-sol-fast": {
        "base": "gpt-5.6-sol",
        "fields": (
            (("id",), "gpt-5.6-sol", "canonical id"),
            (("name",), "GPT-5.6 Sol Fast (ChatGPT OAuth)", "name"),
            (("limit", "context"), 500000, "context limit"),
            (("limit", "input"), 372000, "input limit"),
            (("limit", "output"), 128000, "output limit"),
            (("options", "reasoningEffort"), "xhigh", "xhigh effort"),
            (("options", "serviceTier"), "priority", "Priority tier"),
            (("variants", "max", "reasoningEffort"), "max", "max variant"),
        ),
    },
    "gpt-5.6-terra-fast": {
        "base": "gpt-5.6-terra",
        "fields": (
            (("id",), "gpt-5.6-terra", "canonical id"),
            (("name",), "GPT-5.6 Terra Fast (ChatGPT OAuth)", "name"),
            (("limit", "context"), 500000, "context limit"),
            (("limit", "input"), 372000, "input limit"),
            (("limit", "output"), 128000, "output limit"),
            (("options", "reasoningEffort"), "xhigh", "xhigh effort"),
            (("options", "serviceTier"), "priority", "Priority tier"),
            (("variants", "max", "reasoningEffort"), "max", "max variant"),
        ),
    },
    "gpt-5.6-luna-fast": {
        "base": "gpt-5.6-luna",
        "fields": (
            (("id",), "gpt-5.6-luna", "canonical id"),
            (("name",), "GPT-5.6 Luna Fast (ChatGPT OAuth)", "name"),
            (("limit", "context"), 500000, "context limit"),
            (("limit", "input"), 372000, "input limit"),
            (("limit", "output"), 128000, "output limit"),
            (("options", "reasoningEffort"), "xhigh", "xhigh effort"),
            (("options", "serviceTier"), "priority", "Priority tier"),
            (("variants", "max", "reasoningEffort"), "max", "max variant"),
        ),
    },
    "gpt-5.5-fast": {
        "base": "gpt-5.5",
        "fields": (
            (("id",), "gpt-5.5", "canonical id"),
            (("name",), "GPT-5.5 Fast (ChatGPT OAuth)", "name"),
            (("limit", "context"), 400000, "context limit"),
            (("limit", "input"), 272000, "input limit"),
            (("limit", "output"), 128000, "output limit"),
            (("options", "serviceTier"), "priority", "Priority tier"),
        ),
    },
}

EXPECTED_PRESETS = {
    "custom", "balanced", "premium", "deepseek", "cheap", "openai",
    "openai-fast", "kimi",
}
KIMI_MODEL_REF = "kimi-for-coding/kimi-k3-1m"
SOL_FAST_HIGH_MODEL_REF = "openai/gpt-5.6-sol-fast-high"
KIMI_MODEL_SPEC = {
    "id": "k3[1m]",
    "name": "Kimi K3 1M (Kimi Coding API)",
    "reasoning": True,
    "temperature": False,
    "limit": {"context": 1048576, "output": 131072},
    "modalities": {"input": ["text", "image"], "output": ["text"]},
    "attachment": True,
    "options": {"effort": "max"},
    "variants": {
        "high": {"disabled": True},
        "max": {"disabled": True},
    },
}
OPENROUTER_KIMI_MODEL_SPEC = {
    "name": "Kimi K3 (via OpenRouter)",
    "reasoning": True,
    "temperature": False,
    "limit": {"context": 1048576, "output": 131072},
    "modalities": {"input": ["text", "image"], "output": ["text"]},
    "attachment": True,
}
SOL_FAST_HIGH_MODEL_SPEC = {
    "id": "gpt-5.6-sol",
    "name": "GPT-5.6 Sol Fast High (ChatGPT OAuth)",
    "limit": {"context": 500000, "input": 372000, "output": 128000},
    "options": {"reasoningEffort": "high", "serviceTier": "priority"},
    "variants": {"max": {"disabled": True}},
}
KIMI_COUNCIL_SPEC = {
    "reviewer-1": {"model": KIMI_MODEL_REF},
    "reviewer-2": {"model": "openai/gpt-5.5-fast", "variant": "xhigh"},
    "reviewer-3": {
        "model": "deepseek/deepseek-v4-pro",
        "variant": "max",
    },
}


def check_kimi_profile(
    core: dict,
    slim: dict,
    *,
    expected_default: str | None = None,
) -> tuple[int, int]:
    """Validate the exact K3 preset, intrinsic effort, and fallback alias contract."""
    errors = warnings = 0

    def require(label: str, predicate: bool, detail: str) -> None:
        nonlocal errors, warnings
        errors, warnings = check(
            "CRITICAL", label, predicate, detail, errors, warnings
        )

    def first_model(entry: dict) -> str | None:
        value = entry.get("model") if isinstance(entry, dict) else None
        if isinstance(value, list) and value:
            first = value[0]
            return first.get("id") if isinstance(first, dict) else first
        return value if isinstance(value, str) else None

    def collect_string_paths(value, path: str = "") -> list[tuple[str, str]]:
        found = []
        if isinstance(value, str):
            found.append((path, value))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                found.extend(collect_string_paths(item, f"{path}[{index}]"))
        elif isinstance(value, dict):
            for key, item in value.items():
                child = f"{path}.{key}" if path else key
                found.append((f"{child}#key", str(key)))
                found.extend(collect_string_paths(item, child))
        return found

    presets = slim.get("presets", {})
    council_presets = slim.get("council", {}).get("presets", {})
    require(
        "exact eight agent presets",
        isinstance(presets, dict) and set(presets) == EXPECTED_PRESETS,
        f"expected {sorted(EXPECTED_PRESETS)}",
    )
    require(
        "exact eight council presets",
        isinstance(council_presets, dict)
        and set(council_presets) == EXPECTED_PRESETS,
        f"expected {sorted(EXPECTED_PRESETS)}",
    )

    kimi_models = (
        core.get("provider", {}).get("kimi-for-coding", {}).get("models", {})
    )
    require(
        "sole direct Kimi model is K3 1M",
        isinstance(kimi_models, dict) and set(kimi_models) == {"kimi-k3-1m"},
        "expected only kimi-for-coding/kimi-k3-1m",
    )
    require(
        "exact intrinsic-max K3 model config",
        isinstance(kimi_models, dict)
        and kimi_models.get("kimi-k3-1m") == KIMI_MODEL_SPEC,
        "K3 must map to k3[1m], omit temperature support, use 1M/128K limits, "
        "base effort max, and disable high/max variants",
    )

    openai_models = core.get("provider", {}).get("openai", {}).get("models", {})
    require(
        "exact Sol Fast-high alias config",
        isinstance(openai_models, dict)
        and openai_models.get("gpt-5.6-sol-fast-high")
        == SOL_FAST_HIGH_MODEL_SPEC,
        "alias must map to gpt-5.6-sol with base high effort, Priority tier, "
        "and disabled max",
    )
    unexpected_sol_high_aliases = [
        model_id
        for model_id, model in openai_models.items()
        if isinstance(model, dict)
        and model_id != "gpt-5.6-sol-fast-high"
        and model.get("id") == "gpt-5.6-sol"
        and model.get("options", {}).get("reasoningEffort") == "high"
    ] if isinstance(openai_models, dict) else []
    require(
        "orphaned non-fast Sol-high alias removed",
        not unexpected_sol_high_aliases,
        f"unexpected high-effort Sol aliases: {unexpected_sol_high_aliases}",
    )
    openrouter_models = (
        core.get("provider", {}).get("openrouter", {}).get("models", {})
    )
    require(
        "exact OpenRouter K3 fallback model config",
        isinstance(openrouter_models, dict)
        and openrouter_models.get("moonshotai/kimi-k3")
        == OPENROUTER_KIMI_MODEL_SPEC,
        "OpenRouter K3 must use the configured name, capabilities, 1M/128K "
        "limits, text+image input, text output, and attachments",
    )

    kimi = presets.get("kimi", {}) if isinstance(presets, dict) else {}
    expected_roles = {
        "orchestrator": (KIMI_MODEL_REF, None, None),
        "oracle": ("openai/gpt-5.5-fast", "xhigh", 0.2),
        "librarian": ("openai/gpt-5.6-sol-fast", "high", 0.2),
        "explorer": ("openai/gpt-5.6-sol-fast", "high", 0.1),
        "fixer": ("openai/gpt-5.6-sol-fast", "high", 0.2),
        "designer": ("openai/gpt-5.6-sol-fast", "high", 0.4),
        "observer": ("openai/gpt-5.6-sol-fast", "high", 0.2),
        "council": ("openai/gpt-5.6-sol-fast", "high", 0.2),
    }
    require(
        "exact Kimi preset roles",
        isinstance(kimi, dict) and set(kimi) == set(expected_roles),
        f"expected roles {sorted(expected_roles)}",
    )
    for role, (expected_model, expected_variant, expected_temperature) in expected_roles.items():
        entry = kimi.get(role, {}) if isinstance(kimi, dict) else {}
        require(
            f"Kimi {role} primary model",
            first_model(entry) == expected_model,
            f"expected {expected_model}",
        )
        if expected_variant is None:
            require(
                f"Kimi {role} has no top-level variant",
                "variant" not in entry,
                "intrinsic K3 effort must not be overridden",
            )
        else:
            require(
                f"Kimi {role} variant",
                entry.get("variant") == expected_variant,
                f"expected {expected_variant}",
            )
        if expected_temperature is None:
            require(
                f"Kimi {role} has no temperature",
                "temperature" not in entry,
                "K3 suppresses temperature",
            )
        else:
            require(
                f"Kimi {role} temperature",
                entry.get("temperature") == expected_temperature,
                f"expected {expected_temperature}",
            )

    for preset_name, roles in presets.items() if isinstance(presets, dict) else ():
        if not isinstance(roles, dict):
            continue
        for role, entry in roles.items():
            if first_model(entry) != KIMI_MODEL_REF:
                continue
            require(
                f"Direct K3 primary has no top-level variant: {preset_name}.{role}",
                "variant" not in entry,
                "intrinsic K3 effort must not be overridden",
            )
            require(
                f"Direct K3 primary has no temperature: {preset_name}.{role}",
                "temperature" not in entry,
                "K3 suppresses temperature",
            )

    allowed_alias_paths = {
        "presets.kimi.orchestrator.model[1]",
    }
    alias_paths = {
        path
        for path, value in collect_string_paths(slim)
        if value == SOL_FAST_HIGH_MODEL_REF
    }
    require(
        "Sol Fast-high alias restricted to Kimi first fallbacks",
        alias_paths == allowed_alias_paths,
        f"expected alias only at {sorted(allowed_alias_paths)}; got {sorted(alias_paths)}",
    )
    orchestrator_models = (
        kimi.get("orchestrator", {}).get("model") if isinstance(kimi, dict) else None
    )
    require(
        "Kimi orchestrator first fallback is Sol Fast-high alias",
        isinstance(orchestrator_models, list)
        and len(orchestrator_models) > 1
        and orchestrator_models[1] == SOL_FAST_HIGH_MODEL_REF,
        f"expected {SOL_FAST_HIGH_MODEL_REF} at model[1]",
    )
    expected_fixer_chain = [
        "openai/gpt-5.6-sol-fast",
        KIMI_MODEL_REF,
        "deepseek/deepseek-v4-pro",
        "openrouter/deepseek/deepseek-v4-pro",
        "openrouter/qwen/qwen3-coder:free",
    ]
    fixer_models = kimi.get("fixer", {}).get("model") if isinstance(kimi, dict) else None
    require(
        "exact Kimi fixer fallback chain",
        fixer_models == expected_fixer_chain,
        f"expected {expected_fixer_chain}",
    )

    require(
        "exact Kimi council composition",
        council_presets.get("kimi") == KIMI_COUNCIL_SPEC
        if isinstance(council_presets, dict) else False,
        "expected K3 intrinsic max, GPT-5.5 Fast xhigh, and DeepSeek V4 Pro max",
    )

    kimi_gpt_refs = [
        (path, value)
        for path, value in collect_string_paths({
            "preset": kimi,
            "council": council_presets.get("kimi", {})
            if isinstance(council_presets, dict) else {},
        })
        if value.startswith("openai/gpt-") and "-fast" not in value
    ]
    require(
        "all Kimi GPT routes use Fast/Priority models",
        not kimi_gpt_refs,
        f"non-fast GPT references: {kimi_gpt_refs}",
    )

    active_strings = collect_string_paths(core) + collect_string_paths(slim)
    stale = sorted({
        value
        for _path, value in active_strings
        if "k2.7" in value.lower()
        or "kimi-k2" in value.lower()
        or value == "kimi-for-coding/kimi-for-coding"
    })
    require(
        "no active K2.7 IDs",
        not stale,
        f"stale active values: {stale}",
    )

    if expected_default is not None:
        require(
            "expected Kimi-migration default preset",
            slim.get("preset") == expected_default
            and slim.get("council", {}).get("default_preset") == expected_default,
            f"expected top-level and council default {expected_default!r}",
        )

    return errors, warnings


def check_openai_fast_parity(
    core: dict,
    slim: dict,
    *,
    expected_default: str | None = None,
    baseline: dict | None = None,
    require_fast: bool = False,
) -> tuple[int, int]:
    """Skip absent Fast config by default; reject partial or invalid config."""
    errors = warnings = 0

    def require(label: str, predicate: bool, detail: str) -> None:
        nonlocal errors, warnings
        errors, warnings = check(
            "CRITICAL", label, predicate, detail, errors, warnings
        )

    def normalize_fast_refs(value):
        if isinstance(value, str):
            return OPENAI_FAST_REFERENCE_EQUIVALENCE.get(value, value)
        if isinstance(value, list):
            return [normalize_fast_refs(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize_fast_refs(item) for key, item in value.items()}
        return value

    base_openai_refs = frozenset(OPENAI_FAST_REFERENCE_EQUIVALENCE.values())

    def find_base_openai_refs(value) -> set[str]:
        if isinstance(value, str):
            return {value} if value in base_openai_refs else set()
        if isinstance(value, list):
            found = set()
            for item in value:
                found.update(find_base_openai_refs(item))
            return found
        if isinstance(value, dict):
            found = set()
            for item in value.values():
                found.update(find_base_openai_refs(item))
            return found
        return set()

    models = core.get("provider", {}).get("openai", {}).get("models", {})
    presets = slim.get("presets", {})
    council_presets = slim.get("council", {}).get("presets", {})
    surfaces = {
        **{f"provider.{fast_id}": fast_id in models for fast_id in OPENAI_FAST_SPEC},
        "presets.openai-fast": "openai-fast" in presets,
        "council.openai-fast": "openai-fast" in council_presets,
    }
    if not any(surfaces.values()):
        if require_fast:
            require(
                "OpenAI Fast configuration required",
                False,
                "all Fast provider and preset surfaces are absent",
            )
        return errors, warnings

    require(
        "complete OpenAI Fast configuration",
        all(surfaces.values()),
        "all configured Fast provider aliases, agent preset, and council preset must be present together",
    )
    if not all(surfaces.values()):
        return errors, warnings

    agent_base_refs = find_base_openai_refs(presets["openai-fast"])
    require(
        "openai-fast agent direction",
        not agent_base_refs,
        f"base OpenAI IDs are forbidden: {sorted(agent_base_refs)}",
    )

    council_base_refs = find_base_openai_refs(council_presets["openai-fast"])
    require(
        "openai-fast council direction",
        not council_base_refs,
        f"base OpenAI IDs are forbidden: {sorted(council_base_refs)}",
    )

    require(
        "openai-fast agent parity",
        "openai" in presets
        and normalize_fast_refs(presets["openai-fast"]) == presets.get("openai"),
        "normalized openai-fast agent tree must equal openai",
    )

    require(
        "openai-fast council parity",
        "openai" in council_presets
        and normalize_fast_refs(council_presets["openai-fast"])
        == council_presets.get("openai"),
        "normalized openai-fast council reviewers must equal openai",
    )

    def field_value(model: dict, path: tuple[str, ...]):
        value = model
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    for fast_id, spec in OPENAI_FAST_SPEC.items():
        fast = models[fast_id]
        base_id = spec["base"]
        require(
            f"OpenAI Fast alias object: {fast_id}",
            isinstance(fast, dict),
            "expected an object",
        )
        if not isinstance(fast, dict):
            continue
        for path, expected, label in spec["fields"]:
            require(
                f"OpenAI Fast {label}: {fast_id}",
                field_value(fast, path) == expected,
                f"expected {'.'.join(path)}={expected!r}",
            )

        normalized_fast = copy.deepcopy(fast)
        normalized_fast.pop("id", None)
        normalized_fast.pop("name", None)
        if isinstance(normalized_fast.get("options"), dict):
            normalized_fast["options"].pop("serviceTier", None)
            if not normalized_fast["options"]:
                normalized_fast.pop("options")
        require(
            f"OpenAI Fast provider parity: {fast_id}",
            normalized_fast == models.get(base_id),
            f"alias must otherwise equal {base_id}",
        )

    require(
        "preset/council default parity",
        slim.get("preset") == slim.get("council", {}).get("default_preset"),
        "top-level and council defaults must match",
    )
    if expected_default is not None:
        require(
            "expected default preset",
            slim.get("preset") == expected_default,
            f"expected {expected_default!r}",
        )

    if baseline is not None:
        existing_presets = {
            name: value
            for name, value in presets.items()
            if name not in {"openai-fast", "kimi"}
        }
        existing_council = {
            name: value
            for name, value in council_presets.items()
            if name not in {"openai-fast", "kimi"}
        }
        require(
            "pre-existing preset baseline",
            existing_presets == baseline.get("presets"),
            "a pre-existing generated preset changed",
        )
        require(
            "pre-existing council baseline",
            existing_council == baseline.get("councilPresets"),
            "a pre-existing council preset changed",
        )
        require(
            "baseline default preset",
            slim.get("preset") == baseline.get("defaultPreset"),
            "top-level default changed from checkpoint",
        )
        require(
            "baseline council default",
            slim.get("council", {}).get("default_preset")
            == baseline.get("councilDefault"),
            "council default changed from checkpoint",
        )
        base_models = baseline.get("baseModels", {})
        require(
            "baseline OpenAI Sol provider object",
            models.get("gpt-5.6-sol") == base_models.get("sol"),
            "base Sol provider object changed from checkpoint",
        )
        require(
            "baseline OpenAI Terra provider object",
            models.get("gpt-5.6-terra") == base_models.get("terra"),
            "base Terra provider object changed from checkpoint",
        )
        require(
            "baseline OpenAI Luna provider object",
            models.get("gpt-5.6-luna") == base_models.get("luna"),
            "base Luna provider object changed from checkpoint",
        )
        require(
            "baseline OpenAI GPT-5.5 provider object",
            models.get("gpt-5.5") == base_models.get("gpt-5.5"),
            "base GPT-5.5 provider object changed from checkpoint",
        )

    return errors, warnings


def discover_self_test_configs() -> tuple[Path, Path, str | None]:
    """Find the complete repo or installed-root config pair for self-tests."""
    root = Path(__file__).resolve().parent.parent
    candidates = (
        (
            "repository",
            root / "config" / "opencode.json",
            root / "config" / "oh-my-opencode-slim.json",
            "balanced",
        ),
        (
            "installed",
            root / "opencode.json",
            root / "oh-my-opencode-slim.json",
            None,
        ),
    )
    for _layout, core_path, slim_path, expected_default in candidates:
        if core_path.is_file() and slim_path.is_file():
            return core_path, slim_path, expected_default

    attempted = "; ".join(
        f"{layout}: {core_path}, {slim_path}"
        for layout, core_path, slim_path, _expected_default in candidates
    )
    raise FileNotFoundError(
        f"Self-test requires a complete repository or installed config pair; tried {attempted}"
    )


def run_self_test() -> int:
    """Exercise model references, OpenAI Fast parity, and generator de-dupe."""
    core = {"provider": {"test": {"models": {"one": {}, "two": {}}}}}
    valid = {
        "council": {"presets": {"test": {"reviewer": {"model": [
            "test/one",
            {"id": "test/two", "variant": "high"},
        ]}}}},
    }
    valid_errors, _ = check_referential_integrity(core, valid)
    assert valid_errors == 0, "valid mixed council array was rejected"

    malformed = {
        "council": {"presets": {"test": {"reviewer": {"model": [
            "test/one", "", 7, ["test/one"], {"id": ""},
            {"id": "test/two", "variant": 7},
        ]}}}},
    }
    with contextlib.redirect_stdout(io.StringIO()):
        malformed_errors, _ = check_referential_integrity(core, malformed)
    assert malformed_errors > 0, "malformed model references were accepted"
    _, top_level_object_issues = normalize_model_ref({"id": "test/one"})
    assert top_level_object_issues, "top-level model object was accepted"
    def build_model(fields) -> dict:
        model = {}
        for path, value, _label in fields:
            target = model
            for key in path[:-1]:
                target = target.setdefault(key, {})
            target[path[-1]] = value
        return model

    def base_model(spec: dict) -> dict:
        model = build_model(spec["fields"])
        model.pop("id")
        model.pop("name")
        model["options"].pop("serviceTier")
        if not model["options"]:
            model.pop("options")
        return model

    parity_core = {"provider": {"openai": {"models": {}}}}
    parity_models = parity_core["provider"]["openai"]["models"]
    for fast_id, fast_spec in OPENAI_FAST_SPEC.items():
        parity_models[fast_spec["base"]] = base_model(fast_spec)
        parity_models[fast_id] = build_model(fast_spec["fields"])
    openai_agent = {
        "orchestrator": {
            "model": ["openai/gpt-5.6-sol", "test/fallback"],
            "variant": "xhigh",
        },
        "librarian": {
            "model": [
                "openai/gpt-5.6-sol",
                {"id": "openai/gpt-5.6-terra", "variant": "xhigh"},
            ],
            "variant": "medium",
        },
        "designer": {"model": "openai/gpt-5.6-luna", "variant": "xhigh"},
        "oracle": {"model": "openai/gpt-5.5", "variant": "xhigh"},
    }
    fast_agent = copy.deepcopy(openai_agent)
    fast_agent["orchestrator"]["model"][0] = "openai/gpt-5.6-sol-fast"
    fast_agent["librarian"]["model"][0] = "openai/gpt-5.6-sol-fast"
    fast_agent["librarian"]["model"][1]["id"] = "openai/gpt-5.6-terra-fast"
    fast_agent["designer"]["model"] = "openai/gpt-5.6-luna-fast"
    fast_agent["oracle"]["model"] = "openai/gpt-5.5-fast"
    reviewers = {
        "reviewer-1": {"model": "openai/gpt-5.6-sol"},
        "reviewer-2": {"model": [
            "openai/gpt-5.5",
            {"id": "openai/gpt-5.6-terra", "variant": "high"},
            "openai/gpt-5.6-luna",
            "test/reviewer",
        ]},
    }
    fast_reviewers = copy.deepcopy(reviewers)
    fast_reviewers["reviewer-1"]["model"] = "openai/gpt-5.6-sol-fast"
    fast_reviewers["reviewer-2"]["model"][0] = "openai/gpt-5.5-fast"
    fast_reviewers["reviewer-2"]["model"][1]["id"] = "openai/gpt-5.6-terra-fast"
    fast_reviewers["reviewer-2"]["model"][2] = "openai/gpt-5.6-luna-fast"
    parity_slim = {
        "preset": "openai",
        "presets": {
            "openai": openai_agent,
            "openai-fast": fast_agent,
            "balanced": {"orchestrator": {"model": "test/fallback"}},
        },
        "council": {
            "default_preset": "openai",
            "presets": {
                "openai": reviewers,
                "openai-fast": fast_reviewers,
                "balanced": {"reviewer-1": {"model": "test/reviewer"}},
            },
        },
    }
    baseline = {
        "defaultPreset": "openai",
        "presets": {
            "openai": copy.deepcopy(openai_agent),
            "balanced": {"orchestrator": {"model": "test/fallback"}},
        },
        "councilDefault": "openai",
        "councilPresets": {
            "openai": copy.deepcopy(reviewers),
            "balanced": {"reviewer-1": {"model": "test/reviewer"}},
        },
        "baseModels": {
            "sol": copy.deepcopy(parity_models["gpt-5.6-sol"]),
            "terra": copy.deepcopy(parity_models["gpt-5.6-terra"]),
            "luna": copy.deepcopy(parity_models["gpt-5.6-luna"]),
            "gpt-5.5": copy.deepcopy(parity_models["gpt-5.5"]),
        },
    }
    parity_errors, _ = check_openai_fast_parity(
        parity_core,
        parity_slim,
        expected_default="openai",
        baseline=baseline,
        require_fast=True,
    )
    assert parity_errors == 0, "valid OpenAI Fast parity fixture was rejected"

    absent_core = copy.deepcopy(parity_core)
    absent_slim = copy.deepcopy(parity_slim)
    for fast_id in OPENAI_FAST_SPEC:
        absent_core["provider"]["openai"]["models"].pop(fast_id)
    absent_slim["presets"].pop("openai-fast")
    absent_slim["council"]["presets"].pop("openai-fast")
    assert check_openai_fast_parity(absent_core, absent_slim)[0] == 0
    with contextlib.redirect_stdout(io.StringIO()):
        absent_required = check_openai_fast_parity(
            absent_core, absent_slim, require_fast=True
        )[0]
        partial_core = copy.deepcopy(absent_core)
        first_fast = next(iter(OPENAI_FAST_SPEC))
        partial_core["provider"]["openai"]["models"][first_fast] = copy.deepcopy(
            parity_models[first_fast]
        )
        partial_errors = check_openai_fast_parity(partial_core, absent_slim)[0]
    assert absent_required > 0, "required entirely absent Fast config was accepted"
    assert partial_errors > 0, "partial Fast config was accepted"

    missing = object()
    alias_path = ("provider", "openai", "models", "gpt-5.6-sol-fast")
    field_mutations = (
        ("id", ("id",), "wrong"),
        ("context", ("limit", "context"), 1),
        ("input", ("limit", "input"), 1),
        ("output", ("limit", "output"), 1),
        ("xhigh", ("options", "reasoningEffort"), "high"),
        ("service tier", ("options", "serviceTier"), "default"),
        ("max", ("variants", "max", "reasoningEffort"), "xhigh"),
    )
    mutations = [
        case
        for label, path, wrong in field_mutations
        for case in (
            (f"wrong {label}", "core", alias_path + path, wrong),
            (f"missing {label}", "core", alias_path + path, missing),
        )
    ] + [
        ("literal fast tier", "core", alias_path + ("options", "serviceTier"), "fast"),
        ("agent drift", "slim", ("presets", "openai-fast", "orchestrator", "variant"), "high"),
        ("council drift", "slim", ("council", "presets", "openai-fast", "reviewer-1", "model"), "wrong"),
        ("default drift", "slim", ("preset",), "balanced"),
        ("existing preset drift", "slim", ("presets", "balanced", "orchestrator", "model"), "wrong"),
    ]
    assert len(mutations) == 19

    def mutate(root: dict, path: tuple[str, ...], value) -> None:
        target = root
        for key in path[:-1]:
            target = target[key]
        if value is missing:
            target.pop(path[-1], None)
        else:
            target[path[-1]] = value

    for name, target_name, path, value in mutations:
        mutated_core = copy.deepcopy(parity_core)
        mutated_slim = copy.deepcopy(parity_slim)
        mutate(mutated_core if target_name == "core" else mutated_slim, path, value)
        with contextlib.redirect_stdout(io.StringIO()):
            mutation_errors, _ = check_openai_fast_parity(
                mutated_core,
                mutated_slim,
                expected_default="openai",
                baseline=baseline,
                require_fast=True,
            )
        assert mutation_errors > 0, f"negative mutation was accepted: {name}"

    agent_shapes = {
        "agent string": lambda base: {"model": base},
        "agent list entry": lambda base: {"model": ["test/fallback", base]},
        "agent dict id": lambda base: {
            "model": [{"id": base, "variant": "high"}]
        },
    }
    directional_mutations = 0
    for base in OPENAI_FAST_REFERENCE_EQUIVALENCE.values():
        for label, build_shape in agent_shapes.items():
            mutated_slim = copy.deepcopy(parity_slim)
            shape = build_shape(base)
            mutated_slim["presets"]["openai"]["directional"] = copy.deepcopy(shape)
            mutated_slim["presets"]["openai-fast"]["directional"] = shape
            with contextlib.redirect_stdout(io.StringIO()):
                directional_errors, _ = check_openai_fast_parity(
                    parity_core,
                    mutated_slim,
                    expected_default="openai",
                    require_fast=True,
                )
            assert directional_errors == 1, (
                f"{label} did not directionally reject {base}"
            )
            directional_mutations += 1

        mutated_slim = copy.deepcopy(parity_slim)
        reviewer = {
            "model": ["test/reviewer", {"id": base, "variant": "high"}]
        }
        mutated_slim["council"]["presets"]["openai"]["directional"] = (
            copy.deepcopy(reviewer)
        )
        mutated_slim["council"]["presets"]["openai-fast"]["directional"] = reviewer
        with contextlib.redirect_stdout(io.StringIO()):
            directional_errors, _ = check_openai_fast_parity(
                parity_core,
                mutated_slim,
                expected_default="openai",
                require_fast=True,
            )
        assert directional_errors == 1, (
            f"council structure did not directionally reject {base}"
        )
        directional_mutations += 1
    assert directional_mutations == 16

    generator_path = Path(__file__).with_name("model-profile.py")
    spec = importlib.util.spec_from_file_location("model_profile_self_test", generator_path)
    assert spec and spec.loader, f"cannot load generator: {generator_path}"
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    approved_dedupe = OPENAI_FAST_REFERENCE_EQUIVALENCE
    approved_aliases = {base: fast for fast, base in approved_dedupe.items()}
    assert generator.FAST_MODEL_DEDUPE_EQUIVALENCE == approved_dedupe
    assert generator.KIMI_COUNCIL_MODEL_ALIASES == approved_aliases

    with tempfile.TemporaryDirectory(prefix="model-profile-self-test-") as tmp:
        tmp_path = Path(tmp)
        profile_path = tmp_path / "profile.jsonc"
        output_path = tmp_path / "output.json"
        profile_path.write_text('{"preset":"custom","presets":{}}\n', encoding="utf-8")
        stdout = io.StringIO()
        original_argv = generator.sys.argv
        try:
            generator.sys.argv = [str(generator_path), str(profile_path)]
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
                assert generator.main() == 0
            generator.sys.argv = [str(generator_path), str(profile_path), str(output_path)]
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                assert generator.main() == 0
        finally:
            generator.sys.argv = original_argv
        stdout_bytes = stdout.getvalue().encode("utf-8")
        assert stdout_bytes == output_path.read_bytes(), (
            "stdout and output-file generator modes differ"
        )
        assert stdout_bytes.endswith(b"\n") and not stdout_bytes.endswith(b"\n\n"), (
            "generator stdout must end in exactly one newline"
        )

    null_variant = generator.build_agent_config(
        "fixer", {"model": KIMI_MODEL_REF, "variant": None}, {"fixer": []}
    )
    assert "variant" not in null_variant, "explicit null variant was emitted"
    assert "temperature" not in null_variant, "absent temperature was emitted"
    non_null_variant = generator.build_agent_config(
        "fixer", {"model": KIMI_MODEL_REF, "variant": "max"}, {"fixer": []}
    )
    assert non_null_variant["variant"] == "max", "non-null variant changed"
    default_variant = generator.build_agent_config(
        "fixer", {"model": KIMI_MODEL_REF}, {"fixer": []}
    )
    assert default_variant["variant"] == "high", "default variant behavior changed"

    def generated_models(candidates: list[str]):
        config = generator.build_agent_config(
            "orchestrator",
            {"model": candidates[0]},
            {"orchestrator": candidates[1:]},
        )
        return config["model"]

    for fast, base in approved_dedupe.items():
        assert generated_models([fast, base]) == fast, f"[Fast, base] rewrote {fast}"
        assert generated_models([base, fast]) == base, f"[base, Fast] rewrote {base}"
    unrelated = ["example/model-fast", "example/model"]
    assert generated_models(unrelated) == unrelated, "unrelated -fast ID was de-duplicated"

    base_candidates = [
        "openai/gpt-5.6-sol",
        {"id": "openai/gpt-5.6-terra", "variant": "xhigh"},
        "openai/gpt-5.6-luna",
        "openai/gpt-5.5",
        "example/model",
    ]
    mapped_models = generator.build_presets(
        {"openai-fast": {"designer": {"model": base_candidates[0]}}},
        {"designer": base_candidates[1:]},
    )["openai-fast"]["designer"]["model"]
    assert mapped_models == [
        "openai/gpt-5.6-sol-fast",
        {"id": "openai/gpt-5.6-terra-fast", "variant": "xhigh"},
        "openai/gpt-5.6-luna-fast",
        "openai/gpt-5.5-fast",
        "example/model",
    ], "OpenAI Fast candidate mapping lost aliases or per-model fields"

    generated_council = generator.build_council({
        "presets": {
            "openai": copy.deepcopy(reviewers),
            "openai-fast": copy.deepcopy(reviewers),
            "kimi": copy.deepcopy(reviewers),
        },
    })["presets"]
    assert generated_council["openai"] == reviewers
    assert generated_council["openai-fast"] == fast_reviewers
    assert generated_council["kimi"] == fast_reviewers

    default_kimi_council = generator.build_council(None)["presets"]["kimi"]
    assert default_kimi_council == KIMI_COUNCIL_SPEC, (
        "default Kimi council drifted from the exact Fast/Priority contract"
    )

    def collect_openai_gpt_refs(value) -> list[str]:
        if isinstance(value, str):
            return [value] if value.startswith("openai/gpt-") else []
        if isinstance(value, list):
            return [ref for item in value for ref in collect_openai_gpt_refs(item)]
        if isinstance(value, dict):
            return [ref for item in value.values() for ref in collect_openai_gpt_refs(item)]
        return []

    default_kimi_gpt_refs = collect_openai_gpt_refs(default_kimi_council)
    assert default_kimi_gpt_refs and all(
        "-fast" in ref for ref in default_kimi_gpt_refs
    ), f"default Kimi council retained non-fast GPT refs: {default_kimi_gpt_refs}"

    core_path, slim_path, expected_default = discover_self_test_configs()
    public_core = load_json(str(core_path))
    public_slim = load_json(str(slim_path))
    if expected_default is None:
        expected_default = public_slim.get("preset")
        assert isinstance(expected_default, str) and expected_default, (
            "installed config must declare a non-empty default preset"
        )
    public_errors, _ = check_kimi_profile(
        public_core, public_slim, expected_default=expected_default
    )
    assert public_errors == 0, "valid public Kimi profile was rejected"

    def assert_kimi_mutation_rejected(name: str, edit) -> None:
        mutated_core = copy.deepcopy(public_core)
        mutated_slim = copy.deepcopy(public_slim)
        edit(mutated_core, mutated_slim)
        with contextlib.redirect_stdout(io.StringIO()):
            mutation_errors, _ = check_kimi_profile(
                mutated_core, mutated_slim, expected_default=expected_default
            )
        assert mutation_errors > 0, f"Kimi mutation was accepted: {name}"

    drift_default = "openai-fast" if expected_default != "openai-fast" else "balanced"
    kimi_mutations = {
        "missing agent preset": lambda _core, slim: slim["presets"].pop("cheap"),
        "missing council preset": lambda _core, slim: slim["council"]["presets"].pop("cheap"),
        "K3 effort drift": lambda core, _slim: core["provider"]["kimi-for-coding"]["models"]["kimi-k3-1m"]["options"].update(effort="high"),
        "OpenRouter K3 limit drift": lambda core, _slim: core["provider"]["openrouter"]["models"]["moonshotai/kimi-k3"]["limit"].update(context=1),
        "Fast Sol-high effort drift": lambda core, _slim: core["provider"]["openai"]["models"]["gpt-5.6-sol-fast-high"]["options"].update(reasoningEffort="xhigh"),
        "Fast Sol-high Priority drift": lambda core, _slim: core["provider"]["openai"]["models"]["gpt-5.6-sol-fast-high"]["options"].update(serviceTier="default"),
        "K3 top-level variant": lambda _core, slim: slim["presets"]["kimi"]["orchestrator"].update(variant="max"),
        "non-kimi direct K3 controls": lambda _core, slim: slim["presets"]["custom"]["designer"].update(model=KIMI_MODEL_REF, variant="max", temperature=1.0),
        "wrong first fallback": lambda _core, slim: slim["presets"]["kimi"]["orchestrator"]["model"].__setitem__(1, "openai/gpt-5.6-sol"),
        "alias in Kimi fixer": lambda _core, slim: slim["presets"]["kimi"]["fixer"]["model"].insert(1, SOL_FAST_HIGH_MODEL_REF),
        "non-fast Kimi council GPT": lambda _core, slim: slim["council"]["presets"]["kimi"]["reviewer-2"].update(model="openai/gpt-5.5"),
        "council drift": lambda _core, slim: slim["council"]["presets"]["kimi"]["reviewer-1"].update(variant="max"),
        "default drift": lambda _core, slim: slim.update(preset=drift_default),
        "active K2 ID": lambda core, _slim: core["provider"]["openrouter"]["models"].update({"moonshotai/kimi-k2.7-code": {}}),
    }
    for mutation_name, edit in kimi_mutations.items():
        assert_kimi_mutation_rejected(mutation_name, edit)

    print(
        "Self-test passed: absent/partial gating, 19 Fast parity mutations, "
        "16 directional mutations, exact dedupe map, agent/council alias mapping, "
        "stable-first ordering, byte-identical generator output modes, null-variant "
        "semantics, exact default Kimi council, exact eight-preset Kimi config, "
        "and 14 Kimi negative mutations."
    )
    return 0


def check_api_keys(core: dict, auth_path: str) -> tuple[int, int]:
    """C4: auth.json has a key for every npm-overridden provider."""
    errors = warnings = 0

    try:
        auth = load_json(auth_path)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"  {YELLOW}⚠{RESET} [HIGH] Auth config missing: {auth_path}")
        return errors, warnings + 1

    for pn, pv in core.get("provider", {}).items():
        if "npm" not in pv:
            continue  # native SDK providers use env vars
        # Direct key match (OpenCode stores keys by provider ID)
        if pn in auth and auth[pn]:
            continue
        errors, warnings = check(
            "HIGH",
            f"Missing API key for provider '{pn}'",
            False,
            f"not found in {auth_path}",
            errors, warnings,
        )

    return errors, warnings


def check_zombie_config(slim: dict) -> tuple[int, int]:
    """C5: zombie config — dead temperature fields, deprecated master key."""
    errors = warnings = 0

    # Council temperature (Zod strips it — structurally dead)
    for preset_name, preset in slim.get("council", {}).get("presets", {}).items():
        for role, cfg in preset.items():
            if isinstance(cfg, dict) and "temperature" in cfg:
                errors, warnings = check(
                    "WARNING",
                    f"Zombie config: council.{preset_name}.{role}.temperature",
                    False,
                    "Zod strips temperature from councillor config",
                    errors, warnings,
                )

    # Deprecated master key
    if "master" in slim.get("council", {}):
        errors, warnings = check(
            "WARNING",
            "Zombie config: council.master key",
            False,
            "deprecated — Zod skips it silently",
            errors, warnings,
        )

    return errors, warnings


def check_output_cap() -> tuple[int, int]:
    """Bonus: OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX is set above 32K."""
    errors = warnings = 0
    cap_str = os.environ.get("OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX", "")
    if not cap_str:
        return check(
            "HIGH",
            "OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX is unset",
            False,
            "defaults to 32K — 17/19 models capped below their limits",
            errors, warnings,
        )
    cap = int(cap_str)
    if cap <= 32000:
        return check(
            "HIGH",
            f"OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX={cap} (≤32K)",
            False,
            "17/19 models have output limits above 32K",
            errors, warnings,
        )
    return errors, warnings


# ── main ────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenCode model configuration doctor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Exit 0 = all clear (warnings okay), 1 = errors found.",
    )
    parser.add_argument(
        "--core-config",
        default=os.path.expanduser("~/.config/opencode/opencode.json"),
        help="Path to opencode.json (core model definitions)",
    )
    parser.add_argument(
        "--slim-config",
        default=os.path.expanduser("~/.config/opencode/oh-my-opencode-slim.json"),
        help="Path to oh-my-opencode-slim.json (plugin preset config)",
    )
    parser.add_argument(
        "--auth-config",
        default=os.path.expanduser("~/.local/share/opencode/auth.json"),
        help="Path to auth.json (API keys)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress output; exit code only",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="Run focused model-reference, OpenAI Fast, and Kimi checks",
    )
    parser.add_argument(
        "--expected-default",
        help="Require this top-level and council default preset",
    )
    parser.add_argument(
        "--baseline-manifest",
        help="Immutable Phase 1 baseline manifest for unchanged-object checks",
    )
    parser.add_argument(
        "--baseline-target", choices=("live", "public"),
        help="Manifest section to compare (required with --baseline-manifest)",
    )
    parser.add_argument(
        "--require-openai-fast", action="store_true",
        help="Fail when all OpenAI Fast provider and preset surfaces are absent",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    # Suppress all output in quiet mode
    if args.quiet:
        sys.stdout = open(os.devnull, "w")

    total_errors = 0
    total_warnings = 0

    try:
        core = load_json(args.core_config)
        slim = load_json(args.slim_config)
        baseline = None
        if args.baseline_manifest:
            if not args.baseline_target:
                parser.error("--baseline-target is required with --baseline-manifest")
            baseline = load_json(args.baseline_manifest)[args.baseline_target]
    except Exception as e:
        print(f"  {RED}✗{RESET} [CRITICAL] Cannot load configs: {e}")
        return 1

    print(f"{BOLD}Model config doctor{RESET}")
    print(f"  {DIM}core:  {args.core_config}{RESET}")
    print(f"  {DIM}slim:  {args.slim_config}{RESET}")
    print()

    # ── C1: temperature ──
    e, w = check_temperature(core)
    total_errors += e
    total_warnings += w

    # ── C2: reasoning ──
    e, w = check_reasoning(core)
    total_errors += e
    total_warnings += w

    # ── C3: referential integrity ──
    e, w = check_referential_integrity(core, slim)
    total_errors += e
    total_warnings += w

    # ── OpenAI Fast strict parity ──
    e, w = check_openai_fast_parity(
        core,
        slim,
        expected_default=args.expected_default,
        baseline=baseline,
        require_fast=args.require_openai_fast,
    )
    total_errors += e
    total_warnings += w

    # ── Kimi K3 exact preset and alias contract ──
    e, w = check_kimi_profile(
        core,
        slim,
        expected_default=args.expected_default,
    )
    total_errors += e
    total_warnings += w

    # ── C4: API keys ──
    e, w = check_api_keys(core, args.auth_config)
    total_errors += e
    total_warnings += w

    # ── C5: zombie config ──
    e, w = check_zombie_config(slim)
    total_errors += e
    total_warnings += w

    # ── Bonus: output cap ──
    e, w = check_output_cap()
    total_errors += e
    total_warnings += w

    # ── summary ──
    total_models = sum(
        len(pv["models"]) if isinstance(pv.get("models"), dict) else 0
        for pv in core.get("provider", {}).values()
    )
    print()
    if total_errors == 0 and total_warnings == 0:
        print(f"  {GREEN}✓{RESET} All {total_models} models validated — no issues.")
        return 0
    elif total_errors == 0:
        print(
            f"  {GREEN}✓{RESET} {total_models} models checked, "
            f"{total_warnings} warning(s) need attention."
        )
        return 0
    else:
        print(
            f"  {RED}✗{RESET} {total_models} models checked: "
            f"{total_errors} error(s) — must fix."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
