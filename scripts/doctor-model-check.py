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


def normalize_model_ref(value) -> list[str]:
    """Normalize a model config to a flat list of model ID strings.

    Since v2.0.4, agent `model` may be a string OR an array of strings
    (model-array fallback chains). Fallback `chains` were removed from
    the schema; the array IS the chain.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [m for m in value if isinstance(m, str)]
    return []

def check_temperature(core: dict) -> tuple[int, int]:
    """C1: temperature flag present on every custom-provider (npm) model.

    `temperature: true`  → exposed to the model (pass)
    `temperature: false` → intentional suppression (pass; e.g. K2.7 Code
                            locks temperature at 1.0)
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

    Model references may be a single string or an array of strings
    (v2.0.4 model-array fallback chains). Every element must resolve.

    Note: `fallback.chains` was removed in v2.0.4. Fallback ordering is
    now expressed by the array order on each agent's `model` field.
    """
    errors = warnings = 0
    valid = collect_valid_models(core)

    # council presets
    for preset_name, preset in slim.get("council", {}).get("presets", {}).items():
        for role, entry in preset.items():
            for mid in normalize_model_ref(
                entry.get("model") if isinstance(entry, dict) else None
            ):
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
            for mid in normalize_model_ref(
                agent_cfg.get("model") if isinstance(agent_cfg, dict) else None
            ):
                errors, warnings = check(
                    "CRITICAL",
                    f"Broken reference: preset.{preset_name}.{agent_name} → {mid}",
                    mid in valid,
                    "model not defined in opencode.json",
                    errors, warnings,
                )

    return errors, warnings


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
    args = parser.parse_args()

    # Suppress all output in quiet mode
    if args.quiet:
        sys.stdout = open(os.devnull, "w")

    total_errors = 0
    total_warnings = 0

    try:
        core = load_json(args.core_config)
        slim = load_json(args.slim_config)
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
