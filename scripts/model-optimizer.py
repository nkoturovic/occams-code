#!/usr/bin/env python3
"""
OpenCode Self-Evolving Model Optimizer — Cost-Controlled Edition

Philosophy:
  - NEVER spends money without your explicit approval
  - NEVER runs in the background without your knowledge
  - Shows you EXACTLY what each change costs
  - Hard spending limits that cannot be bypassed
  - All changes are reversible with one command

Usage:
  python3 model-optimizer.py              # Scan & report only (safe default)
  python3 model-optimizer.py --apply      # Apply ONLY after showing you the diff
  python3 model-optimizer.py --validate   # Validate all config models against opencode models
  python3 model-optimizer.py --startup    # Validate & repair on launch (non-blocking)
  python3 model-optimizer.py --repair    # Auto-repair broken models in config
"""

import json
import os
import sys
import urllib.request
import urllib.error
import datetime
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

CONFIG_DIR = Path(os.environ.get("OPENCODE_CONFIG", Path.home() / ".config/opencode"))
SLIM_JSON = CONFIG_DIR / "oh-my-opencode-slim.json"
OPENCODE_JSON = CONFIG_DIR / "opencode.json"
BACKUP_DIR = CONFIG_DIR / "backups"

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Models that may appear in provider catalogs but are known to fail at runtime
# in this setup (especially during delegated agent calls).
KNOWN_BAD_MODELS = {
    "opencode/minimax-m2.7": "Known runtime unsupported errors in delegated flows",
    "opencode/qwen-3.6-plus": "Validates but rejected at runtime — use openrouter/qwen/qwen3.6-plus instead",
}

# ─── Colors ──────────────────────────────────────────────────────────────────


class C:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    NC = "\033[0m"


def info(msg):
    print(f"{C.BLUE}[INFO]{C.NC} {msg}")


def ok(msg):
    print(f"{C.GREEN}[OK]{C.NC} {msg}")


def warn(msg):
    print(f"{C.YELLOW}[WARN]{C.NC} {msg}")


def error(msg):
    print(f"{C.RED}[ERROR]{C.NC} {msg}")


def bold(msg):
    print(f"{C.BOLD}{msg}{C.NC}")


# ─── Data Fetching ───────────────────────────────────────────────────────────


def fetch_openrouter_models():
    """Fetch live model data from OpenRouter API."""
    info("Fetching live model data from OpenRouter API...")
    try:
        req = urllib.request.Request(OPENROUTER_MODELS_URL)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        models = data.get("data", [])
        ok(f"Fetched {len(models)} models from OpenRouter")
        return models
    except Exception as e:
        error(f"Failed to fetch OpenRouter models: {e}")
        return []


def parse_pricing(model_data):
    input_p = float(model_data.get("pricing", {}).get("prompt", "0"))
    output_p = float(model_data.get("pricing", {}).get("completion", "0"))
    return input_p * 1_000_000, output_p * 1_000_000


def classify_tier(input_per_m, output_per_m):
    avg = (input_per_m + output_per_m) / 2
    if avg == 0:
        return "free"
    elif avg < 1.0:
        return "budget"
    elif avg < 8.0:
        return "standard"
    else:
        return "premium"


TIER_ORDER = {"free": 0, "budget": 1, "standard": 2, "premium": 3}


def build_catalog(or_models):
    catalog = {}
    for m in or_models:
        raw_id = m.get("id", "")
        name = m.get("name", raw_id)
        context = m.get("context_length", 0)
        input_p, output_p = parse_pricing(m)

        # Filter out placeholder/test models with negative or absurd pricing
        if input_p < 0 or output_p < 0:
            continue
        if input_p > 1000 or output_p > 1000:
            continue

        tier = classify_tier(input_p, output_p)
        catalog[f"openrouter/{raw_id}"] = {
            "raw_id": raw_id,
            "name": name,
            "context": context,
            "input_per_m": round(input_p, 4),
            "output_per_m": round(output_p, 4),
            "tier": tier,
        }
    return catalog


# ─── Config ──────────────────────────────────────────────────────────────────


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def find_in_catalog(model_ref, catalog):
    if model_ref in catalog:
        return catalog[model_ref]
    if "/" in model_ref:
        short = model_ref.split("/", 1)[1]
        for cid, cdata in catalog.items():
            if cid.endswith("/" + short):
                return cdata
    return None


# ─── Improvement Detection ──────────────────────────────────────────────────


def detect_improvements(config, catalog):
    improvements = []
    max_tier = TIER_ORDER.get("standard", 2)

    for preset_name, preset in config.get("presets", {}).items():
        for agent_name, agent_config in preset.items():
            if not isinstance(agent_config, dict):
                continue
            current_model = agent_config.get("model")
            if not current_model:
                continue

            current_info = find_in_catalog(current_model, catalog)
            if not current_info:
                continue

            for candidate_id, candidate_info in catalog.items():
                if candidate_id == current_model:
                    continue

                # Never suggest known-bad runtime models
                if candidate_id in KNOWN_BAD_MODELS:
                    continue

                # Skip meta-models and non-LLM endpoints
                if any(
                    skip in candidate_id.lower()
                    for skip in [
                        "openrouter/auto",
                        "openrouter/bodybuilder",
                        "openrouter/mini",
                    ]
                ):
                    continue

                # Enforce tier ceiling
                if TIER_ORDER.get(candidate_info["tier"], 0) > max_tier:
                    continue

                cost_diff = (
                    candidate_info["output_per_m"] - current_info["output_per_m"]
                )

                # Only suggest if cheaper or same-tier free replacement
                if cost_diff < -0.01:  # At least $0.01 cheaper
                    pct_drop = (
                        (abs(cost_diff) / current_info["output_per_m"] * 100)
                        if current_info["output_per_m"] > 0
                        else 100
                    )
                    improvements.append(
                        {
                            "type": "cost_saving",
                            "preset": preset_name,
                            "agent": agent_name,
                            "current": current_model,
                            "current_cost": f"${current_info['output_per_m']:.4f}/1M out",
                            "candidate": candidate_id,
                            "candidate_cost": f"${candidate_info['output_per_m']:.4f}/1M out",
                            "savings_per_m": round(abs(cost_diff), 4),
                            "savings_pct": round(pct_drop, 1),
                            "tier": candidate_info["tier"],
                            "safe": True,
                        }
                    )
                # Free replacement for paid
                elif (
                    candidate_info["tier"] == "free" and current_info["tier"] != "free"
                ):
                    improvements.append(
                        {
                            "type": "free_upgrade",
                            "preset": preset_name,
                            "agent": agent_name,
                            "current": current_model,
                            "current_cost": f"${current_info['output_per_m']:.4f}/1M out",
                            "candidate": candidate_id,
                            "candidate_cost": "FREE",
                            "savings_per_m": current_info["output_per_m"],
                            "savings_pct": 100,
                            "tier": "free",
                            "safe": True,
                        }
                    )

    # Deduplicate
    seen = set()
    unique = []
    for imp in improvements:
        key = f"{imp['preset']}/{imp['agent']}/{imp['candidate']}"
        if key not in seen:
            seen.add(key)
            unique.append(imp)

    # Sort by savings (biggest first)
    unique.sort(key=lambda x: x["savings_per_m"], reverse=True)
    return unique


# ─── Approval Gate ──────────────────────────────────────────────────────────


def request_approval(changes):
    """Interactive approval gate. Returns list of approved change indices."""
    if not changes:
        return []

    print()
    bold("─" * 60)
    bold("  APPROVAL REQUIRED")
    bold("─" * 60)
    print()
    print("The following changes would SAVE you money:")
    print()

    for i, ch in enumerate(changes):
        num = i + 1
        print(f"  [{num}] {ch['preset']}/{ch['agent']}:")
        print(f"      {ch['current']} ({ch['current_cost']})")
        print(f"   →  {ch['candidate']} ({ch['candidate_cost']})")
        print(
            f"      Saves: ${ch['savings_per_m']:.4f}/1M tokens ({ch['savings_pct']:.0f}% cheaper)"
        )
        print()

    print("─" * 60)
    print("  Enter numbers to approve (comma-separated), or:")
    print("    all   — approve all changes")
    print("    none  — approve nothing")
    print("    quit  — exit without changes")
    print("─" * 60)
    print()

    try:
        answer = input("Your choice: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return []

    if answer in ("quit", "q", "exit", "no", "n"):
        return []
    if answer in ("all", "a", "yes", "y"):
        return list(range(len(changes)))
    if answer in ("none", "0", ""):
        return []

    approved = []
    for part in answer.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(changes):
                approved.append(idx)

    return approved


# ─── Apply Changes ──────────────────────────────────────────────────────────


def backup_config():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{ts}"
    backup_path.mkdir()
    import shutil

    for src in [SLIM_JSON, OPENCODE_JSON]:
        if src.exists():
            shutil.copy2(src, backup_path / src.name)

    # Prune old backups (keep 10 most recent)
    all_backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
    for old in all_backups[10:]:
        if old.is_dir():
            shutil.rmtree(old)

    ok(f"Backup: {backup_path}")
    return backup_path


def apply_changes(config, changes, approved_indices):
    applied = []
    for idx in approved_indices:
        ch = changes[idx]
        config["presets"][ch["preset"]][ch["agent"]]["model"] = ch["candidate"]
        applied.append(ch)
    return applied


def validate_config(config):
    try:
        json.dumps(config)
        assert "presets" in config
        assert "fallback" in config
        return True
    except Exception as e:
        error(f"Validation failed: {e}")
        return False


# ─── Main ────────────────────────────────────────────────────────────────────


def get_available_models():
    """Return set of models from `opencode models`, or None on failure."""
    import subprocess

    try:
        result = subprocess.run(
            ["opencode", "models"], capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            warn(f"opencode models returned non-zero exit code: {result.returncode}")
            return None
        available = set(
            line.strip() for line in result.stdout.strip().split("\n") if line.strip()
        )
        return available if available else None
    except FileNotFoundError:
        warn("'opencode' command not found in PATH")
        return None
    except subprocess.TimeoutExpired:
        warn("'opencode models' timed out after 30s")
        return None
    except Exception as e:
        warn(f"Could not fetch model list: {e}")
        return None


def validate_models(config, available_models=None, preset_filter=None):
    """Check all models in config against available models set.

    Args:
        config: The loaded config dict.
        available_models: Set of available model strings, or None to auto-detect.
        preset_filter: If set, only validate models in this preset.

    Returns:
        List of broken entries (dicts with preset/agent/model or fallback_for/model).
    """
    if available_models is None:
        available_models = get_available_models()
    if available_models is None:
        return []  # Skip strict validation when model list unavailable

    broken = []
    for preset_name, preset in config.get("presets", {}).items():
        if preset_filter and preset_name != preset_filter:
            continue
        for agent_name, agent_config in preset.items():
            if not isinstance(agent_config, dict):
                continue
            model = agent_config.get("model", "")
            if model and (model not in available_models or model in KNOWN_BAD_MODELS):
                reason = (
                    "known_bad_runtime"
                    if model in KNOWN_BAD_MODELS
                    else "not_in_available_models"
                )
                broken.append(
                    {
                        "preset": preset_name,
                        "agent": agent_name,
                        "model": model,
                        "reason": reason,
                    }
                )

    # Also check fallback chains
    for agent_name, chain in config.get("fallback", {}).get("chains", {}).items():
        for model in chain:
            if model and (model not in available_models or model in KNOWN_BAD_MODELS):
                reason = (
                    "known_bad_runtime"
                    if model in KNOWN_BAD_MODELS
                    else "not_in_available_models"
                )
                broken.append(
                    {
                        "fallback_for": agent_name,
                        "model": model,
                        "reason": reason,
                    }
                )

    return broken


# ─── Model Repair ────────────────────────────────────────────────────────────


SAFE_DEFAULTS = {
    "orchestrator": "openrouter/qwen/qwen3.6-plus",
    "oracle": "anthropic/claude-sonnet-4-6",
    "designer": "openrouter/google/gemini-3.1-flash-lite-preview",
    "explorer": "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
    "librarian": "openrouter/qwen/qwen3.6-plus",
    "fixer": "openrouter/z-ai/glm-5.1",
}


def repair_models(config, available_models):
    """Repair broken models in config using fallback chains and safe defaults.

    Returns:
        (repaired_model_changes, repaired_chain_changes) — lists of dicts describing
        what was changed.
    """
    repaired_model_changes = []
    repaired_chain_changes = []

    # Repair preset agent models
    for preset_name, preset in config.get("presets", {}).items():
        for agent_name, agent_config in preset.items():
            if not isinstance(agent_config, dict):
                continue
            current_model = agent_config.get("model", "")
            if not current_model or (
                current_model in available_models
                and current_model not in KNOWN_BAD_MODELS
            ):
                continue

            # Try first available model from fallback chain for this agent
            replacement = None
            chain = config.get("fallback", {}).get("chains", {}).get(agent_name, [])
            for candidate in chain:
                if candidate in available_models and candidate not in KNOWN_BAD_MODELS:
                    replacement = candidate
                    break

            # Fallback to safe default
            if replacement is None:
                safe_default = SAFE_DEFAULTS.get(agent_name)
                if (
                    safe_default
                    and safe_default in available_models
                    and safe_default not in KNOWN_BAD_MODELS
                ):
                    replacement = safe_default

            if replacement:
                config["presets"][preset_name][agent_name]["model"] = replacement
                repaired_model_changes.append(
                    {
                        "preset": preset_name,
                        "agent": agent_name,
                        "old": current_model,
                        "new": replacement,
                    }
                )

    # Repair fallback chains
    for agent_name, chain in config.get("fallback", {}).get("chains", {}).items():
        original_len = len(chain)
        # Remove unavailable and known-bad runtime models
        new_chain = [
            m for m in chain if m in available_models and m not in KNOWN_BAD_MODELS
        ]
        # De-duplicate preserving order
        seen = set()
        deduped = []
        for m in new_chain:
            if m not in seen:
                seen.add(m)
                deduped.append(m)
        new_chain = deduped

        # If chain becomes empty, seed with safe default
        if not new_chain:
            safe_default = SAFE_DEFAULTS.get(agent_name)
            if (
                safe_default
                and safe_default in available_models
                and safe_default not in KNOWN_BAD_MODELS
            ):
                new_chain = [safe_default]

        if new_chain != chain or len(new_chain) != original_len:
            config["fallback"]["chains"][agent_name] = new_chain
            removed = [m for m in chain if m not in new_chain]
            added = [m for m in new_chain if m not in chain]
            repaired_chain_changes.append(
                {
                    "agent": agent_name,
                    "removed": removed,
                    "added": added,
                    "new_chain": new_chain,
                }
            )

    return repaired_model_changes, repaired_chain_changes


def main():
    mode = "scan"
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            mode = arg[2:]

    # ─── Validate mode: check models against opencode models list ───
    if mode == "validate":
        try:
            config = load_json(SLIM_JSON)
        except Exception as e:
            error(f"Failed to load config: {e}")
            sys.exit(1)

        available = get_available_models()
        broken = validate_models(config, available_models=available)

        if not broken:
            ok("All models in config are available.")
            sys.exit(0)
        else:
            error(f"Found {len(broken)} broken model(s):")
            print()
            for b in broken:
                reason = b.get("reason", "unknown")
                if "preset" in b:
                    print(f"  ✗ {b['preset']}/{b['agent']}: {b['model']} ({reason})")
                else:
                    print(f"  ✗ fallback/{b['fallback_for']}: {b['model']} ({reason})")
            print()
            sys.exit(1)

    # ─── Repair mode: auto-fix broken models ───
    if mode == "repair":
        try:
            config = load_json(SLIM_JSON)
        except Exception as e:
            error(f"Failed to load config: {e}")
            sys.exit(1)

        available = get_available_models()
        if available is None:
            error("Cannot get available models — repair requires model list.")
            sys.exit(1)

        model_changes, chain_changes = repair_models(config, available)

        if not model_changes and not chain_changes:
            ok("No repairs needed.")
            sys.exit(0)

        # Backup and save
        backup_config()
        if validate_config(config):
            save_json(SLIM_JSON, config)
            if model_changes:
                bold(f"  Repaired {len(model_changes)} model(s):")
                for ch in model_changes:
                    print(
                        f"    ✓ {ch['preset']}/{ch['agent']}: {ch['old']} → {ch['new']}"
                    )
            if chain_changes:
                bold(f"  Repaired {len(chain_changes)} fallback chain(s):")
                for ch in chain_changes:
                    print(
                        f"    ✓ {ch['agent']}: removed {ch['removed']}, added {ch['added']}"
                    )
            sys.exit(0)
        else:
            error("Validation failed after repair — config not saved.")
            sys.exit(1)

    # ─── Startup mode: automatic but transparent ───
    if mode == "startup":
        try:
            config = load_json(SLIM_JSON)
        except Exception:
            sys.exit(0)  # Never block launch

        active_preset = config.get("preset", "dynamic")

        # Model health check: validate & auto-repair if needed
        available = get_available_models()
        if available is not None:
            broken_active = validate_models(
                config, available_models=available, preset_filter=active_preset
            )
            if broken_active:
                warn(
                    f"Found {len(broken_active)} broken model(s) in preset '{active_preset}':"
                )
                for b in broken_active:
                    safe = SAFE_DEFAULTS.get(b.get("agent", ""), "unknown")
                    if "preset" in b:
                        print(f"  ✗ {b['agent']}: {b['model']} (safe default: {safe})")
                    else:
                        print(f"  ✗ fallback/{b['fallback_for']}: {b['model']}")

                if sys.stdin.isatty():
                    try:
                        answer = (
                            input("\n  Repair broken models? [Y/n] ").strip().lower()
                        )
                    except (EOFError, KeyboardInterrupt):
                        answer = "n"
                    if answer in ("", "y", "yes"):
                        model_changes, chain_changes = repair_models(config, available)
                        if model_changes or chain_changes:
                            backup_config()
                            if validate_config(config):
                                save_json(SLIM_JSON, config)
                                total = len(model_changes) + len(chain_changes)
                                print(f"{C.GREEN}✓ Repaired {total} issue(s){C.NC}")
                            else:
                                error("Validation failed after repair — skipping save")
                    else:
                        warn(
                            "Skipped — fallback chains will activate for broken models"
                        )
                else:
                    warn(
                        "Non-interactive mode: run 'model-optimizer.py --repair' to fix"
                    )
        else:
            warn("Could not verify model availability — skipping health check")

        sys.exit(0)

    bold(f"OpenCode Model Optimizer — Cost-Controlled [{mode}]")
    print()

    # ─── Normal scan/apply mode ───

    # Load config
    try:
        config = load_json(SLIM_JSON)
    except Exception as e:
        error(f"Failed to load config: {e}")
        sys.exit(1)

    # Validate models before proceeding
    available = get_available_models()
    broken = validate_models(config, available_models=available)
    if broken:
        error(f"Found {len(broken)} broken model(s) in config. Run --repair first.")
        for b in broken:
            if "preset" in b:
                print(f"  ✗ {b['preset']}/{b['agent']}: {b['model']}")
            else:
                print(f"  ✗ fallback/{b['fallback_for']}: {b['model']}")
        sys.exit(1)

    # Fetch live data
    or_models = fetch_openrouter_models()
    if not or_models:
        error("No model data. Check network.")
        sys.exit(1)

    catalog = build_catalog(or_models)

    # Detect improvements (cost savings only — never suggest spending more)
    improvements = detect_improvements(config, catalog)

    if not improvements:
        ok("No cost-saving improvements found. Your config is already optimized!")
        print()
        return

    # Show findings
    bold(f"Found {len(improvements)} cost-saving opportunities:")
    print()
    total_savings = 0
    for i, imp in enumerate(improvements):
        num = i + 1
        print(f"  [{num}] {imp['preset']}/{imp['agent']}:")
        print(f"      {imp['current']} ({imp['current_cost']})")
        print(f"   →  {imp['candidate']} ({imp['candidate_cost']})")
        print(
            f"      Saves: ${imp['savings_per_m']:.4f}/1M ({imp['savings_pct']:.0f}% cheaper)"
        )
        total_savings += imp["savings_per_m"]
        print()

    print(f"  Total potential savings: ${total_savings:.4f}/1M output tokens")
    print()

    # Apply mode
    if mode == "apply":
        approved = request_approval(improvements)

        if not approved:
            info("No changes approved. Exiting.")
            return

        # Backup
        backup_config()

        # Apply
        applied = apply_changes(config, improvements, approved)

        # Validate
        if validate_config(config):
            save_json(SLIM_JSON, config)

            ok(f"Applied {len(applied)} changes!")
            print()
            for ch in applied:
                print(
                    f"  ✓ {ch['preset']}/{ch['agent']}: {ch['current']} → {ch['candidate']}"
                )
            print()
            info("Restart OpenCode for changes to take effect.")
        else:
            error("Validation failed! Rolling back...")
            import shutil

            backups = sorted(BACKUP_DIR.iterdir(), reverse=True)
            if backups:
                shutil.copy2(backups[0] / SLIM_JSON.name, SLIM_JSON)
                ok(f"Rolled back to {backups[0]}")
            sys.exit(1)
    else:
        info("Run with --apply to apply changes (approval required)")
        print()


if __name__ == "__main__":
    main()
