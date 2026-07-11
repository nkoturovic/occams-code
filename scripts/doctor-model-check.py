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
}


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

    canonical_refs = {
        f"openai/{fast}": f"openai/{spec['base']}"
        for fast, spec in OPENAI_FAST_SPEC.items()
    }

    def normalize_fast_refs(value):
        if isinstance(value, str):
            return canonical_refs.get(value, value)
        if isinstance(value, list):
            return [normalize_fast_refs(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize_fast_refs(item) for key, item in value.items()}
        return value

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
        "both aliases, agent preset, and council preset must be present together",
    )
    if not all(surfaces.values()):
        return errors, warnings

    require(
        "openai-fast agent parity",
        "openai" in presets
        and normalize_fast_refs(presets["openai-fast"]) == presets.get("openai"),
        "normalized openai-fast agent tree must equal openai",
    )

    require(
        "openai-fast council parity",
        "openai" in council_presets
        and council_presets["openai-fast"] == council_presets.get("openai"),
        "openai-fast council reviewers must exactly equal openai",
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
            name: value for name, value in presets.items() if name != "openai-fast"
        }
        existing_council = {
            name: value
            for name, value in council_presets.items()
            if name != "openai-fast"
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

    return errors, warnings


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
        }
    }
    fast_agent = copy.deepcopy(openai_agent)
    fast_agent["orchestrator"]["model"][0] = "openai/gpt-5.6-sol-fast"
    reviewers = {"reviewer-1": {"model": "test/reviewer"}}
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
                "openai-fast": copy.deepcopy(reviewers),
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

    generator_path = Path(__file__).with_name("model-profile.py")
    spec = importlib.util.spec_from_file_location("model_profile_self_test", generator_path)
    assert spec and spec.loader, f"cannot load generator: {generator_path}"
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    approved_dedupe = {
        f"openai/{fast}": f"openai/{fast_spec['base']}"
        for fast, fast_spec in OPENAI_FAST_SPEC.items()
    }
    assert generator.FAST_MODEL_DEDUPE_EQUIVALENCE == approved_dedupe

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

    print(
        "Self-test passed: absent/partial gating, 19 independent Fast parity "
        "mutations, exact dedupe map, and Sol/Terra stable-first ordering."
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
        help="Run focused model-reference and OpenAI Fast parity checks",
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
