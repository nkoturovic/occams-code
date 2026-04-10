#!/usr/bin/env python3
"""Quick provider health + credit check for oc launcher.

Checks in parallel (~3-5s total):
  1. OpenRouter credit balance (via /api/v1/auth/key)
  2. Each provider's API reachability (via /models or /v1/models endpoint)

Silent when all OK. Shows warnings for dead providers or low credits.

Usage:
  python3 provider-health.py          # Human-readable (quiet if all OK)
  python3 provider-health.py --all    # Show all results even when healthy
  python3 provider-health.py --json   # Machine-readable output
"""

import json
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

AUTH_FILE = Path.home() / ".local/share/opencode/auth.json"
CONFIG_FILE = Path.home() / ".config/opencode/oh-my-opencode-slim.json"
OPENCODE_JSON = Path.home() / ".config/opencode/opencode.json"

# Low credit threshold (USD) — warn below this
LOW_CREDIT_THRESHOLD = 1.0

# Provider API endpoints for health pings (just check if API responds)
PROVIDER_ENDPOINTS = {
    "openrouter": "https://openrouter.ai/api/v1/models",
    "deepseek": "https://api.deepseek.com/v1/models",
    "anthropic": "https://api.anthropic.com/v1/models",
    "openai": "https://api.openai.com/v1/models",
}


def _load_auth() -> dict:
    """Load API keys from auth.json."""
    try:
        data = json.loads(AUTH_FILE.read_text())
        keys = {}
        for provider, val in data.items():
            if isinstance(val, dict):
                # OpenCode uses 'key', some formats use 'apiKey'
                k = val.get("key") or val.get("apiKey") or ""
                if k:
                    keys[provider] = k
            elif isinstance(val, str) and val:
                keys[provider] = val
        return keys
    except Exception:
        return {}


def _get_active_providers() -> set:
    """Get providers actually used in active preset + fallback chains."""
    providers = set()
    try:
        config = json.loads(CONFIG_FILE.read_text())
        preset_name = config.get("preset", "balanced")
        preset = config.get("presets", {}).get(preset_name, {})
        for agent_cfg in preset.values():
            model = agent_cfg.get("model", "")
            if "/" in model:
                providers.add(model.split("/")[0])
        for chain in config.get("fallback", {}).get("chains", {}).values():
            for model in chain:
                if "/" in model:
                    providers.add(model.split("/")[0])
    except Exception:
        pass
    return providers


def _check_openrouter_credits(api_key: str) -> dict:
    """Check OpenRouter credit balance via API."""
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            info = data.get("data", {})
            balance = info.get("limit_remaining")
            usage = info.get("usage")

            limit = info.get("limit")
            if balance is not None:
                return {
                    "alive": True,
                    "balance": round(balance, 4),
                    "usage": round(usage, 4) if usage is not None else None,
                    "limit": round(limit, 2) if limit is not None else None,
                    "low": balance < LOW_CREDIT_THRESHOLD,
                }
            # No limit field = unlimited or free-tier-only account
            if usage is not None:
                return {
                    "alive": True,
                    "balance": None,
                    "usage": round(usage, 4),
                    "low": False,
                    "note": "no credit limit set (free tier?)",
                }
            return {"alive": True, "balance": None, "usage": None, "low": False}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"alive": False, "error": "invalid API key"}
        return {"alive": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"alive": False, "error": str(e)[:80]}


def _ping_provider(provider: str, api_key: str | None) -> dict:
    """Check if a provider's API endpoint is reachable."""
    url = PROVIDER_ENDPOINTS.get(provider)
    if not url:
        return {"alive": True, "note": "no endpoint to test (opencode proxy)"}

    headers = {}
    if api_key:
        if provider == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return {"alive": True}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"alive": False, "error": "invalid API key"}
        if e.code == 403:
            return {"alive": False, "error": "access denied (check credits/plan)"}
        if e.code == 429:
            return {"alive": True, "note": "rate limited but reachable"}
        # Some providers return 4xx for /models but are actually working
        if e.code < 500:
            return {"alive": True, "note": f"HTTP {e.code} (likely OK)"}
        return {"alive": False, "error": f"server error ({e.code})"}
    except urllib.error.URLError as e:
        return {"alive": False, "error": f"unreachable: {e.reason}"}
    except Exception as e:
        return {"alive": False, "error": str(e)[:80]}


def main():
    show_all = "--all" in sys.argv
    json_mode = "--json" in sys.argv

    auth = _load_auth()
    active = _get_active_providers()
    # Test active providers by default, --all tests every configured provider
    test_providers = set(auth.keys()) if show_all else active

    results = {}
    or_credits = None

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {}

        # Check credits for OpenRouter
        if "openrouter" in auth:
            futures[pool.submit(_check_openrouter_credits, auth["openrouter"])] = (
                "_or_credits"
            )

        # Ping providers
        for provider in test_providers:
            if provider in PROVIDER_ENDPOINTS:
                key = auth.get(provider)
                futures[pool.submit(_ping_provider, provider, key)] = provider

        for future in as_completed(futures):
            tag = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = {"alive": False, "error": str(e)[:80]}

            if tag == "_or_credits":
                or_credits = result
            else:
                results[tag] = result

    if json_mode:
        print(
            json.dumps(
                {"providers": results, "openrouter_credits": or_credits}, indent=2
            )
        )
        return 0

    # Determine if anything needs attention
    has_issues = False
    lines = []

    # Credit check
    if or_credits:
        if not or_credits.get("alive"):
            lines.append(
                f"  \033[31m✗\033[0m OpenRouter: {or_credits.get('error', '?')}"
            )
            has_issues = True
        elif or_credits.get("low"):
            bal = or_credits.get("balance", "?")
            lines.append(
                f"  \033[33m⚠\033[0m OpenRouter credits low: ${bal} remaining — paid models may fail"
            )
            lines.append(f"      Top up: https://openrouter.ai/settings/credits")
            lines.append(f"      Free models in fallback chains will still work.")
            has_issues = True
        elif show_all:
            bal = or_credits.get("balance")
            note = or_credits.get("note", "")
            if bal is not None:
                lines.append(f"  \033[32m✓\033[0m OpenRouter: ${bal} credits")
            elif note:
                lines.append(f"  \033[32m✓\033[0m OpenRouter: {note}")
            else:
                lines.append(f"  \033[32m✓\033[0m OpenRouter: OK")

    # Provider pings
    for provider in sorted(results):
        r = results[provider]
        if not r.get("alive"):
            lines.append(f"  \033[31m✗\033[0m {provider}: {r.get('error', '?')}")
            has_issues = True
        elif show_all:
            note = r.get("note", "OK")
            lines.append(f"  \033[32m✓\033[0m {provider}: {note}")

    if has_issues or (show_all and lines):
        for line in lines:
            print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
