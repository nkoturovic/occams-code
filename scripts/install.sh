#!/usr/bin/env bash
#
# occams-code installer
# Copies scripts, config, wiki template, and generates opencode.json
#
set -euo pipefail

BOLD='\033[1m'
DIM='\033[2m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENCODE_DIR="$HOME/.config/opencode"
WIKI_DIR="$HOME/wiki"

echo ""
echo -e "${BOLD}  Occam's Code installer${RESET}"
echo -e "  ${DIM}───────────────────${RESET}"
echo ""

# --- Dependency checks ---
for cmd in python3 jq fzf curl; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}Error: $cmd is required but not installed.${RESET}" >&2
    exit 1
  fi
done

# Bash version check
if [[ "${BASH_VERSINFO[0]:-0}" -lt 4 ]]; then
  echo -e "${RED}Error: bash 4.0+ required (current: ${BASH_VERSION}).${RESET}" >&2
  echo -e "  macOS: brew install bash" >&2
  exit 1
fi

echo -e "Source: ${GREEN}$REPO_ROOT${RESET}"
echo -e "Target: ${GREEN}$OPENCODE_DIR${RESET}"
echo -e "Wiki:   ${GREEN}$WIKI_DIR${RESET}"
echo ""

# --- Create directories ---
mkdir -p "$OPENCODE_DIR"/{bin,scripts,commands}
mkdir -p "$WIKI_DIR"/{raw/{articles,papers,repos,docs,forums,assets,_inbox},wiki/{projects,domain,languages,patterns,concepts,entities,sources,comparisons}}

# --- Copy files ---
echo -e "${BOLD}Copying files...${RESET}"

# bin/oc
cp "$REPO_ROOT/bin/oc" "$OPENCODE_DIR/bin/oc"
chmod +x "$OPENCODE_DIR/bin/oc"
echo -e "  ${GREEN}✓${RESET} bin/oc"

# Scripts
cp "$REPO_ROOT"/scripts/*.py "$OPENCODE_DIR/scripts/"
chmod +x "$OPENCODE_DIR/scripts/generate-config.py"
echo -e "  ${GREEN}✓${RESET} scripts/ ($(ls "$REPO_ROOT"/scripts/*.py | wc -l) files)"

# Commands
cp "$REPO_ROOT"/commands/*.md "$OPENCODE_DIR/commands/"
echo -e "  ${GREEN}✓${RESET} commands/ ($(ls "$REPO_ROOT"/commands/*.md | wc -l) files)"

# Config
if [[ -f "$REPO_ROOT/config/oh-my-opencode-slim.json" ]]; then
  cp "$REPO_ROOT/config/oh-my-opencode-slim.json" "$OPENCODE_DIR/oh-my-opencode-slim.json"
  echo -e "  ${GREEN}✓${RESET} oh-my-opencode-slim.json"
else
  echo -e "  ${YELLOW}⚠${RESET} config/oh-my-opencode-slim.json not found (skip)"
fi

# AGENTS.md
cp "$REPO_ROOT/AGENTS.md" "$OPENCODE_DIR/AGENTS.md"
echo -e "  ${GREEN}✓${RESET} AGENTS.md"

# --- Generate opencode.json ---
echo ""
echo -e "${BOLD}Generating opencode.json...${RESET}"
python3 "$OPENCODE_DIR/scripts/generate-config.py"
echo -e "  ${GREEN}✓${RESET} opencode.json generated"

# --- Wiki template ---
echo ""
echo -e "${BOLD}Setting up wiki template...${RESET}"

# Copy wiki files (don't overwrite existing)
for f in AGENTS.md index.md overview.md log.md .gitignore; do
  if [[ -f "$REPO_ROOT/wiki/$f" ]]; then
    if [[ ! -f "$WIKI_DIR/$f" ]]; then
      cp "$REPO_ROOT/wiki/$f" "$WIKI_DIR/$f"
      echo -e "  ${GREEN}✓${RESET} wiki/$f"
    else
      echo -e "  ${YELLOW}⊙${RESET} wiki/$f (already exists, skipped)"
    fi
  fi
done

# Copy wiki content (with overwrite protection)
for f in wiki/wiki/concepts/karpathy-llm-wiki.md wiki/wiki/sources/_template-source-summary.md wiki/raw/README.md; do
  if [[ -f "$REPO_ROOT/$f" ]]; then
    target="$WIKI_DIR/$f"
    target_dir="$(dirname "$target")"
    mkdir -p "$target_dir"
    if [[ ! -f "$target" ]]; then
      cp "$REPO_ROOT/$f" "$target"
      echo -e "  ${GREEN}✓${RESET} $f"
    else
      echo -e "  ${YELLOW}⊙${RESET} $f (already exists, skipped)"
    fi
  fi
done

# Copy patterns (with overwrite protection)
if [[ -d "$REPO_ROOT/wiki/wiki/patterns" ]]; then
  for f in "$REPO_ROOT"/wiki/wiki/patterns/*.md; do
    [[ -f "$f" ]] || continue
    basename="$(basename "$f")"
    target="$WIKI_DIR/wiki/patterns/$basename"
    if [[ ! -f "$target" ]]; then
      cp "$f" "$target"
      echo -e "  ${GREEN}✓${RESET} wiki/wiki/patterns/$basename"
    else
      echo -e "  ${YELLOW}⊙${RESET} wiki/wiki/patterns/$basename (already exists, skipped)"
    fi
  done
fi

# .gitkeep files
find "$WIKI_DIR" -type d -empty -exec touch {}/.gitkeep \; 2>/dev/null || true

# --- Install oh-my-opencode-slim ---
echo ""
echo -e "${BOLD}Installing oh-my-opencode-slim plugin...${RESET}"
cd "$OPENCODE_DIR"
if command -v bun &>/dev/null; then
  bun install oh-my-opencode-slim 2>/dev/null && echo -e "  ${GREEN}✓${RESET} Installed via bun" || echo -e "  ${YELLOW}⚠${RESET} bun install failed (install manually)"
elif command -v npm &>/dev/null; then
  npm install oh-my-opencode-slim 2>/dev/null && echo -e "  ${GREEN}✓${RESET} Installed via npm" || echo -e "  ${YELLOW}⚠${RESET} npm install failed (install manually)"
else
  echo -e "  ${YELLOW}⚠${RESET} Neither bun nor npm found. Install oh-my-opencode-slim manually."
fi

# --- Done ---
echo ""
echo -e "${GREEN}Installation complete!${RESET}"
echo ""
echo "Next steps:"
echo "  1. Set up API keys (run 'opencode' once to configure)"
echo "  2. Run: oc --doctor"
echo "  3. Open ~/wiki/ in Obsidian (optional)"
echo "  4. Launch: oc"
echo ""
