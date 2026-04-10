#!/usr/bin/env python3
"""
OpenCode Role-Aware Model Picker

Builds a sorted, tagged model list for fzf display, prioritizing models
recommended for the given agent role.

Usage:
  opencode models | python3 role-picker.py <agent> <current_model> [pricing_file]

  agent          Agent role (orchestrator, oracle, designer, explorer, librarian, fixer)
  current_model  Currently configured model for this agent
  pricing_file   Path to OpenRouter pricing cache JSON (default: auto-generated /tmp path)

Output:
  Header comments + sorted tagged lines, one model per line.
"""

import sys
import os
import json
import argparse
from datetime import date


# ─── Role-aware recommendations (April 2026 landscape) ────────────────────────

ROLE_BEST = {
    "orchestrator": {
        "best": ["qwen-3.6-plus", "glm-5.1", "claude-sonnet-4-6"],
        "budget": ["qwen-3.5-omni", "deepseek-v3.2"],
        "reason": "Needs good reasoning + instruction following",
    },
    "oracle": {
        "best": ["claude-opus-4-6", "claude-sonnet-4-6", "glm-5.1"],
        "budget": ["deepseek-v3.2", "qwen-3.6-plus"],
        "reason": "Needs deep reasoning + low hallucination",
    },
    "designer": {
        "best": ["gemini-3.1-flash", "gemini-3.1-pro", "claude-sonnet-4-6"],
        "budget": ["gemini-3-flash", "qwen-3.6-plus"],
        "reason": "Needs creativity + UI understanding",
    },
    "explorer": {
        "best": ["nemotron-3-super-free", "qwen-3.6-plus", "deepseek-v3.2"],
        "budget": ["nemotron-3-super-free", "deepseek-v3.2"],
        "reason": "Speed + cost matter most, basic comprehension",
    },
    "librarian": {
        "best": ["qwen-3.6-plus", "nemotron-3-super-free", "deepseek-v3.2"],
        "budget": ["nemotron-3-super-free", "deepseek-v3.2"],
        "reason": "Doc synthesis + accuracy, free is fine",
    },
    "fixer": {
        "best": ["glm-5.1", "qwen-3.6-plus", "claude-sonnet-4-6"],
        "budget": ["deepseek-v3.2", "qwen-3.5-omni"],
        "reason": "Coding ability + tool use reliability",
    },
}


def load_pricing(or_file):
    """Load OpenRouter pricing data from cached JSON, returning {short_name: (tier, price_str)}."""
    pricing = {}
    if not os.path.exists(or_file):
        return pricing
    try:
        with open(or_file) as f:
            data = json.load(f)
        for m in data.get("data", []):
            mid = m["id"]
            p = m.get("pricing", {})
            inp = float(p.get("prompt", 0)) * 1_000_000
            out = float(p.get("completion", 0)) * 1_000_000
            avg = (inp + out) / 2
            if avg == 0:
                tier = "free"
            elif avg < 1:
                tier = "budget"
            elif avg < 8:
                tier = "standard"
            else:
                tier = "premium"
            short = mid.split("/")[-1]
            price_str = f"${inp:.2f}/${out:.2f}"
            pricing[short] = (tier, price_str)
            pricing[short.replace(".", "-")] = (tier, price_str)
    except Exception:
        pass
    return pricing


def build_picker(agent, current, pricing):
    """Build sorted, tagged model lines for the given agent role."""
    role_info = ROLE_BEST.get(agent, {"best": [], "budget": [], "reason": ""})
    best_set = set(role_info["best"])
    budget_set = set(role_info["budget"])

    lines = []
    for line in sys.stdin:
        model = line.strip()
        if not model:
            continue
        short = model.split("/", 1)[-1] if "/" in model else model
        tier, price = pricing.get(short, ("unknown", "$?/$?"))

        # Determine priority for ordering
        if model == current:
            priority = 0
        elif short in best_set:
            priority = 1
        elif short in budget_set:
            priority = 2
        elif tier == "free":
            priority = 3
        elif tier == "budget":
            priority = 4
        elif tier == "standard":
            priority = 5
        else:
            priority = 6

        # Tag
        tag = ""
        if model == current:
            tag = "← current"
        elif short in best_set:
            tag = "★ recommended"
        elif short in budget_set:
            tag = "💰 budget pick"
        elif tier == "free":
            tag = "🆓 free"

        lines.append((priority, f"{model:<50} [{tier:<8}] {price:<16} {tag}"))

    # Sort: priority first, then alphabetically
    lines.sort(key=lambda x: (x[0], x[1]))

    # Print header
    reason = role_info.get("reason", "")
    print(f"# {agent.upper()} — {reason}")
    print(f"# ★ = recommended  💰 = budget  🆓 = free  ← = current")
    print("#" + "-" * 80)
    for _, line in lines:
        print(line)


def main():
    parser = argparse.ArgumentParser(description="Role-aware model picker for OpenCode")
    parser.add_argument(
        "agent",
        help="Agent role (orchestrator, oracle, designer, explorer, librarian, fixer)",
    )
    parser.add_argument(
        "current_model", help="Currently configured model for this agent"
    )
    parser.add_argument(
        "pricing_file",
        nargs="?",
        default=f"/tmp/oc-or-pricing-{date.today().strftime('%Y%m%d')}.json",
        help="Path to OpenRouter pricing cache JSON",
    )
    args = parser.parse_args()

    pricing = load_pricing(args.pricing_file)
    build_picker(args.agent, args.current_model, pricing)


if __name__ == "__main__":
    main()
