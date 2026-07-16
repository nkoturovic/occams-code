#!/usr/bin/env bash
#
# occams-code installer
# Interactive or unattended installation of OpenCode scripts, config, and dependencies.
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
OPENCODE_DIR="${OCCAM_OPENCODE_DIR:-$HOME/.config/opencode}"
AGENTS_DIR="$HOME/.agents"

SECRETS_DIR="$HOME/.config/secrets"
SECRETS_FILE="$SECRETS_DIR/env"

# ── Defaults ─────────────────────────────────────────────────────────
UNATTENDED=0
DRY_RUN=0

# These will be filled from CLI, env vars, or interactive prompts
PROVIDERS=""
PRESET=""
INSTALL_DEFUDDLE=1
INSTALL_AGENT_BROWSER=1
INSTALL_OBSIDIAN=1
SETUP_CRON=1
SETUP_PATH=1
ENABLE_ZAI_MCPS=0
ZAI_KEY=""
SETUP_SECRETS=1

# Preserve-only configs are never modified when already present.
OPENCODE_CONFIG_PREEXISTED=0
SLIM_CONFIG_PREEXISTED=0
PROFILE_CONFIG_PREEXISTED=0
[[ -f "$OPENCODE_DIR/opencode.json" ]] && OPENCODE_CONFIG_PREEXISTED=1
[[ -f "$OPENCODE_DIR/oh-my-opencode-slim.json" ]] && SLIM_CONFIG_PREEXISTED=1
[[ -f "$OPENCODE_DIR/model-profile.jsonc" ]] && PROFILE_CONFIG_PREEXISTED=1

# ── Helpers ──────────────────────────────────────────────────────────
_usage() {
  echo "Usage: $0 [--unattended] [--dry-run] [--preset NAME] [--providers CSV] [--no-defuddle] [--no-agent-browser] [--no-obsidian] [--no-cron] [--no-path] [--enable-zai] [--zai-key KEY]"
}

_ask_yes_no() {
  local prompt="$1"
  local default="${2:-Y}"
  local answer
  if [[ "$default" == "Y" ]]; then
    read -rp "$prompt [Y/n] " answer < /dev/tty
    answer="${answer:-Y}"
  else
    read -rp "$prompt [y/N] " answer < /dev/tty
    answer="${answer:-N}"
  fi
  case "$answer" in
    [Yy]|[Yy][Ee][Ss]) return 0 ;;
    *) return 1 ;;
  esac
}

_ask_hidden() {
  local prompt="$1"
  local varname="$2"
  local value
  read -rsp "$prompt" value < /dev/tty
  echo "" >&2
  printf -v "$varname" '%s' "$value"
}

# ── CLI argument parsing ─────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)         _usage; exit 0 ;;
    --unattended)      UNATTENDED=1; shift ;;
    --dry-run)         DRY_RUN=1; shift ;;
    --preset)          PRESET="$2"; shift 2 ;;
    --providers)       PROVIDERS="$2"; shift 2 ;;
    --no-defuddle)     INSTALL_DEFUDDLE=0; shift ;;
    --no-agent-browser) INSTALL_AGENT_BROWSER=0; shift ;;
    --no-obsidian)     INSTALL_OBSIDIAN=0; shift ;;
    --no-cron)         SETUP_CRON=0; shift ;;
    --no-path)         SETUP_PATH=0; shift ;;
    --enable-zai)      ENABLE_ZAI_MCPS=1; shift ;;
    --zai-key)         ZAI_KEY="$2"; shift 2 ;;
    *)
      echo -e "${RED}Unknown option: $1${RESET}" >&2
      _usage >&2
      exit 1
      ;;
  esac
done

# ── Unattended: env vars (CLI flags override env vars) ───────────────
if [[ "$UNATTENDED" -eq 1 ]]; then
  [[ -z "$PROVIDERS" ]]       && PROVIDERS="${OCCAM_PROVIDERS:-openrouter}"
  [[ -z "$PRESET" ]]          && PRESET="${OCCAM_PRESET:-balanced}"
  [[ -z "$ZAI_KEY" ]]         && ZAI_KEY="${OCCAM_ZAI_API_KEY:-}"

  # Booleans: env vars override defaults only if CLI didn't explicitly set
  # We detect CLI by checking if the value differs from default... but that's fragile.
  # Instead: in unattended mode, env vars ALWAYS apply unless the corresponding CLI flag was passed.
  # Since we can't easily distinguish "not passed" from "default value" for booleans,
  # we use the convention that unattended mode reads all booleans from env vars.
  INSTALL_DEFUDDLE="${OCCAM_INSTALL_DEFUDDLE:-$INSTALL_DEFUDDLE}"
  INSTALL_AGENT_BROWSER="${OCCAM_INSTALL_AGENT_BROWSER:-$INSTALL_AGENT_BROWSER}"
  INSTALL_OBSIDIAN="${OCCAM_INSTALL_OBSIDIAN:-$INSTALL_OBSIDIAN}"
  SETUP_CRON="${OCCAM_SETUP_CRON:-$SETUP_CRON}"
  SETUP_PATH="${OCCAM_SETUP_PATH:-$SETUP_PATH}"
  ENABLE_ZAI_MCPS="${OCCAM_ENABLE_ZAI_MCPS:-$ENABLE_ZAI_MCPS}"
  SETUP_SECRETS="${OCCAM_SETUP_SECRETS:-$SETUP_SECRETS}"

  if [[ "$ENABLE_ZAI_MCPS" -eq 1 && -z "$ZAI_KEY" ]]; then
    echo -e "${RED}Error: OCCAM_ZAI_API_KEY is required when OCCAM_ENABLE_ZAI_MCPS=1${RESET}" >&2
    exit 1
  fi

  # Deepseek preset needs OpenRouter for designer/observer
  if [[ "$PRESET" == "deepseek" && "$PROVIDERS" != *"openrouter"* ]]; then
    echo -e "${YELLOW}Note: deepseek preset requires OpenRouter. Adding to providers.${RESET}" >&2
    PROVIDERS="${PROVIDERS:+$PROVIDERS,}openrouter"
  fi
  if [[ "$PRESET" == "kimi" ]]; then
    if [[ "$PROVIDERS" != *"kimi"* ]]; then
      echo -e "${YELLOW}Note: kimi preset requires Kimi. Adding to providers.${RESET}" >&2
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}kimi"
    fi
    if [[ "$PROVIDERS" != *"openai"* ]]; then
      echo -e "${YELLOW}Note: kimi preset uses OpenAI support roles. Adding to providers.${RESET}" >&2
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}openai"
    fi
    if [[ "$PROVIDERS" != *"deepseek"* ]]; then
      echo -e "${YELLOW}Note: kimi preset uses direct DeepSeek fallbacks/council. Adding to providers.${RESET}" >&2
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}deepseek"
    fi
  fi
fi

# ── Header ───────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}  Occam's Code installer${RESET}"
echo -e "  ${DIM}───────────────────${RESET}"
echo ""

# ── Dependency checks ────────────────────────────────────────────────
for cmd in python3 jq curl git; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}Error: $cmd is required but not installed.${RESET}" >&2
    exit 1
  fi
done

# Bash version check (installer works on 3.2+, but bin/oc requires 4+)
if [[ "${BASH_VERSINFO[0]:-0}" -lt 4 ]]; then
  echo -e "${YELLOW}Warning: bash ${BASH_VERSION} detected. bin/oc requires bash 4.0+.${RESET}" >&2
  echo -e "  The installer will succeed, but you must run oc with bash 5:" >&2
  echo -e "  macOS: /opt/homebrew/bin/bash ~/.config/opencode/bin/oc" >&2
  echo "" >&2
fi

# ── Interactive questions ────────────────────────────────────────────
if [[ "$UNATTENDED" -eq 0 ]]; then
  echo -e "${BOLD}Interactive setup${RESET} (press Enter for defaults)"
  echo ""

  # Q1: API providers
  echo "Q1. Which API providers will you use?"
  echo "  1) OpenRouter"
  echo "  2) DeepSeek"
  echo "  3) Anthropic"
  echo "  4) Z.AI"
  echo "  5) Kimi"
  echo "  6) OpenAI (ChatGPT Plus OAuth via /connect)"
  read -rp "  Enter space-separated numbers [1]: " _q1 < /dev/tty
  _q1="${_q1:-1}"
  PROVIDERS=""
  for n in $_q1; do
    case "$n" in
      1) PROVIDERS="${PROVIDERS:+$PROVIDERS,}openrouter" ;;
      2) PROVIDERS="${PROVIDERS:+$PROVIDERS,}deepseek" ;;
      3) PROVIDERS="${PROVIDERS:+$PROVIDERS,}anthropic" ;;
      4) PROVIDERS="${PROVIDERS:+$PROVIDERS,}zai" ;;
      5) PROVIDERS="${PROVIDERS:+$PROVIDERS,}kimi" ;;
      6) PROVIDERS="${PROVIDERS:+$PROVIDERS,}openai" ;;
    esac
  done
  [[ -z "$PROVIDERS" ]] && PROVIDERS="openrouter"
  echo -e "  ${GREEN}→${RESET} $PROVIDERS"
  echo ""

  # Auto-recommend preset
  _rec="balanced"
  if [[ "$PROVIDERS" == *"kimi"* && "$PROVIDERS" == *"openai"* && "$PROVIDERS" == *"deepseek"* ]]; then
    _rec="kimi"
  elif [[ "$PROVIDERS" == *"openai"* ]]; then
    _rec="openai"
  elif [[ "$PROVIDERS" == *"anthropic"* ]]; then
    _rec="premium"
  elif [[ "$PROVIDERS" == *"deepseek"* && "$PROVIDERS" != *"openrouter"* ]]; then
    _rec="deepseek"
  elif [[ "$PROVIDERS" == *"kimi"* && "$PROVIDERS" == *"zai"* ]]; then
    _rec="custom"
  fi

  # Q2: Default preset
  case "$_rec" in
    cheap)     _def_num=2 ;;
    deepseek)  _def_num=3 ;;
    premium)   _def_num=4 ;;
    custom)    _def_num=5 ;;
    openai)    _def_num=6 ;;
    kimi)      _def_num=8 ;;
    *)         _def_num=1 ;;
  esac

  echo "Q2. Select default preset:"
  echo "  1) balanced  $([[ "$_rec" == "balanced" ]] && echo -e "${GREEN}(recommended)${RESET}" || echo "")"
  echo "  2) cheap"
  echo "  3) deepseek"
  echo "  4) premium   $([[ "$_rec" == "premium" ]] && echo -e "${GREEN}(recommended)${RESET}" || echo "")"
  echo "  5) custom    $([[ "$_rec" == "custom" ]] && echo -e "${GREEN}(recommended)${RESET}" || echo "")"
  echo "  6) openai     $([[ "$_rec" == "openai" ]] && echo -e "${GREEN}(recommended)${RESET}" || echo "") (ChatGPT Plus OAuth via /connect)"
  echo "  7) openai-fast (opt-in OAuth Fast/Priority; increased usage)"
  echo "  8) kimi       $([[ "$_rec" == "kimi" ]] && echo -e "${GREEN}(recommended)${RESET}" || echo "") (K3 1M + OpenAI support roles)"
  read -rp "  Enter number [$_def_num]: " _q2 < /dev/tty
  _q2="${_q2:-$_def_num}"
  case "$_q2" in
    2) PRESET="cheap" ;;
    3) PRESET="deepseek" ;;
    4) PRESET="premium" ;;
    5) PRESET="custom" ;;
    6) PRESET="openai" ;;
    7) PRESET="openai-fast" ;;
    8) PRESET="kimi" ;;
    *) PRESET="balanced" ;;
  esac
  echo -e "  ${GREEN}→${RESET} $PRESET"

  # Warn if deepseek preset needs OpenRouter but it's not in providers
  if [[ "$PRESET" == "deepseek" && "$PROVIDERS" != *"openrouter"* ]]; then
    echo -e "  ${YELLOW}⚠${RESET} The deepseek preset uses OpenRouter for designer/observer. Adding openrouter to providers."
    PROVIDERS="${PROVIDERS:+$PROVIDERS,}openrouter"
  fi
  if [[ "$PRESET" == "kimi" ]]; then
    if [[ "$PROVIDERS" != *"kimi"* ]]; then
      echo -e "  ${YELLOW}⚠${RESET} The kimi preset requires Kimi. Adding kimi to providers."
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}kimi"
    fi
    if [[ "$PROVIDERS" != *"openai"* ]]; then
      echo -e "  ${YELLOW}⚠${RESET} The kimi preset uses OpenAI support roles. Adding openai to providers."
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}openai"
    fi
    if [[ "$PROVIDERS" != *"deepseek"* ]]; then
      echo -e "  ${YELLOW}⚠${RESET} The kimi preset uses direct DeepSeek fallbacks/council. Adding deepseek to providers."
      PROVIDERS="${PROVIDERS:+$PROVIDERS,}deepseek"
    fi
  fi
  echo ""

  # Q3: Z.AI MCPs
  if [[ "$PROVIDERS" == *"zai"* ]]; then
    if _ask_yes_no "Q3. Enable Z.AI MCPs (zai_vision + web-search-prime)?" "N"; then
      ENABLE_ZAI_MCPS=1
      _ask_hidden "  Enter Z.AI API key: " ZAI_KEY
      echo -e "  ${GREEN}→${RESET} enabled"
    else
      ENABLE_ZAI_MCPS=0
      echo -e "  ${DIM}→ skipped${RESET}"
    fi
    echo ""
  fi

  # Q4: Optional CLIs
  echo "Q4. Optional CLIs:"
  if _ask_yes_no "  Install defuddle (HTML-to-markdown)?" "Y"; then
    INSTALL_DEFUDDLE=1
  else
    INSTALL_DEFUDDLE=0
  fi
  if _ask_yes_no "  Install agent-browser (web browsing)?" "Y"; then
    INSTALL_AGENT_BROWSER=1
  else
    INSTALL_AGENT_BROWSER=0
  fi
  if _ask_yes_no "  Install Obsidian (wiki viewer)?" "Y"; then
    INSTALL_OBSIDIAN=1
  else
    INSTALL_OBSIDIAN=0
  fi
  echo ""

  # Q5: Weekly cron
  if _ask_yes_no "Q5. Set up weekly log cleanup cron job?" "Y"; then
    SETUP_CRON=1
  else
    SETUP_CRON=0
  fi
  echo ""

  # Q6: PATH setup
  if _ask_yes_no "Q6. Add oc to your shell PATH (~/.bashrc / ~/.zshrc)?" "Y"; then
    SETUP_PATH=1
  else
    SETUP_PATH=0
  fi
  echo ""

  # Q7: Shared env-secrets
  if _ask_yes_no "Q7. Set up API keys in ~/.config/secrets/env?" "Y"; then
    SETUP_SECRETS=1
  else
    SETUP_SECRETS=0
  fi
  echo ""
fi

# Validate preset before summary/dry-run.
if [[ -n "${PRESET:-}" ]]; then
  case "$PRESET" in
    custom|balanced|cheap|premium|deepseek|openai|openai-fast|kimi) ;;
    *) echo -e "${RED}Error: unknown preset '$PRESET'${RESET}" >&2; exit 1 ;;
  esac
fi

_bundled_config() {
  local name="$1"
  if [[ -f "$REPO_ROOT/config/$name" ]]; then
    printf '%s\n' "$REPO_ROOT/config/$name"
  elif [[ -f "$REPO_ROOT/$name" ]]; then
    printf '%s\n' "$REPO_ROOT/$name"
  else
    return 1
  fi
}

_effective_config() {
  local name="$1"
  if [[ -f "$OPENCODE_DIR/$name" ]]; then
    printf '%s\n' "$OPENCODE_DIR/$name"
  else
    _bundled_config "$name"
  fi
}

_fast_config_error() {
  echo -e "${RED}Error: openai-fast is unavailable in the effective configuration.${RESET}" >&2
  echo "  Upgrade or merge opencode.json, oh-my-opencode-slim.json, and model-profile.jsonc, then retry; no files were changed." >&2
  exit 1
}

if [[ "$PRESET" == "openai-fast" ]]; then
  _fast_core="$(_effective_config opencode.json)" || _fast_config_error
  _fast_slim="$(_effective_config oh-my-opencode-slim.json)" || _fast_config_error
  _fast_profile="$(_effective_config model-profile.jsonc)" || _fast_config_error
  _fast_doctor="$REPO_ROOT/scripts/doctor-model-check.py"
  _fast_generator="$REPO_ROOT/scripts/model-profile.py"

  [[ -f "$_fast_doctor" && -f "$_fast_generator" ]] || _fast_config_error

  if ! python3 "$_fast_doctor" \
      --core-config "$_fast_core" \
      --slim-config "$_fast_slim" \
      --require-openai-fast \
      --quiet; then
    _fast_config_error
  fi

  if ! python3 "$_fast_generator" "$_fast_profile" 2>/dev/null |
      python3 "$_fast_doctor" \
        --core-config "$_fast_core" \
        --slim-config /dev/stdin \
        --require-openai-fast \
        --quiet; then
    _fast_config_error
  fi
fi

_kimi_config_error() {
  echo -e "${RED}Error: kimi is unavailable in the effective configuration.${RESET}" >&2
  echo "  Upgrade or merge opencode.json, oh-my-opencode-slim.json, and model-profile.jsonc, then retry; no files were changed." >&2
  exit 1
}

if [[ "$PRESET" == "kimi" ]]; then
  _kimi_core="$(_effective_config opencode.json)" || _kimi_config_error
  _kimi_slim="$(_effective_config oh-my-opencode-slim.json)" || _kimi_config_error
  _kimi_profile="$(_effective_config model-profile.jsonc)" || _kimi_config_error
  _kimi_doctor="$REPO_ROOT/scripts/doctor-model-check.py"
  _kimi_generator="$REPO_ROOT/scripts/model-profile.py"

  [[ -f "$_kimi_doctor" && -f "$_kimi_generator" ]] || _kimi_config_error

  if ! python3 "$_kimi_doctor" \
      --core-config "$_kimi_core" \
      --slim-config "$_kimi_slim" \
      --quiet; then
    _kimi_config_error
  fi

  if ! python3 "$_kimi_generator" "$_kimi_profile" 2>/dev/null |
      python3 "$_kimi_doctor" \
        --core-config "$_kimi_core" \
        --slim-config /dev/stdin \
        --quiet; then
    _kimi_config_error
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────
echo -e "${BOLD}Summary${RESET}"
echo "  Providers:       $PROVIDERS"
echo "  Preset:          $PRESET"
echo "  Z.AI MCPs:       $([[ $ENABLE_ZAI_MCPS -eq 1 ]] && echo "enabled" || echo "disabled")"
[[ -n "$ZAI_KEY" ]] && echo "  Z.AI key:        ***set***"
echo "  defuddle:        $([[ $INSTALL_DEFUDDLE -eq 1 ]] && echo "yes" || echo "no")"
echo "  agent-browser:   $([[ $INSTALL_AGENT_BROWSER -eq 1 ]] && echo "yes" || echo "no")"
echo "  Obsidian:        $([[ $INSTALL_OBSIDIAN -eq 1 ]] && echo "yes" || echo "no")"
echo "  Cron cleanup:    $([[ $SETUP_CRON -eq 1 ]] && echo "yes" || echo "no")"
echo "  PATH setup:      $([[ $SETUP_PATH -eq 1 ]] && echo "yes" || echo "no")"
echo "  Secrets setup:   $([[ $SETUP_SECRETS -eq 1 ]] && echo "yes" || echo "no")"
echo ""

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo -e "${YELLOW}Dry run — no changes made.${RESET}"
  exit 0
fi

if [[ "$UNATTENDED" -eq 0 ]]; then
  if ! _ask_yes_no "Proceed with installation?" "Y"; then
    echo -e "${YELLOW}Aborted.${RESET}"
    exit 0
  fi
  echo ""
fi

# ── Create directories ───────────────────────────────────────────────
mkdir -p "$OPENCODE_DIR"/{bin,scripts,commands,skills}
mkdir -p "$SECRETS_DIR"
mkdir -p "$HOME/.local/bin"

echo -e "Source: ${GREEN}$REPO_ROOT${RESET}"
echo -e "Target: ${GREEN}$OPENCODE_DIR${RESET}"
echo ""

# ── Copy files ───────────────────────────────────────────────────────
echo -e "${BOLD}Copying files...${RESET}"

# bin/oc — always overwrite
cp "$REPO_ROOT/bin/oc" "$OPENCODE_DIR/bin/oc"
chmod +x "$OPENCODE_DIR/bin/oc"
echo -e "  ${GREEN}✓${RESET} bin/oc"

# Scripts — always overwrite
if ls "$REPO_ROOT"/scripts/*.py &>/dev/null; then
  cp "$REPO_ROOT"/scripts/*.py "$OPENCODE_DIR/scripts/"
  echo -e "  ${GREEN}✓${RESET} scripts/*.py ($(ls "$REPO_ROOT"/scripts/*.py 2>/dev/null | wc -l) files)"
fi
if [[ -f "$REPO_ROOT/scripts/cleanup-logs.sh" ]]; then
  cp "$REPO_ROOT/scripts/cleanup-logs.sh" "$OPENCODE_DIR/scripts/cleanup-logs.sh"
  chmod +x "$OPENCODE_DIR/scripts/cleanup-logs.sh"
  echo -e "  ${GREEN}✓${RESET} cleanup-logs.sh"
fi

# Commands — always overwrite
if ls "$REPO_ROOT"/commands/*.md &>/dev/null; then
  cp "$REPO_ROOT"/commands/*.md "$OPENCODE_DIR/commands/"
  echo -e "  ${GREEN}✓${RESET} commands/ ($(ls "$REPO_ROOT"/commands/*.md 2>/dev/null | wc -l) files)"
fi

# Config files — preserve if exist
_preserve_copy() {
  local src="$1"
  local dst="$2"
  local label="$3"
  if [[ -f "$src" ]]; then
    if [[ ! -f "$dst" ]]; then
      cp "$src" "$dst"
      echo -e "  ${GREEN}✓${RESET} $label"
    else
      echo -e "  ${YELLOW}⊙${RESET} $label (already exists, skipped)"
    fi
  else
    echo -e "  ${YELLOW}⚠${RESET} $label not found in source"
  fi
}

_preserve_bundled_config() {
  local name="$1"
  local src
  if src="$(_bundled_config "$name")"; then
    _preserve_copy "$src" "$OPENCODE_DIR/$name" "$name"
  else
    echo -e "  ${YELLOW}⚠${RESET} $name not found in source"
  fi
}

_preserve_bundled_config "opencode.json"
_preserve_bundled_config "oh-my-opencode-slim.json"
_preserve_copy "$REPO_ROOT/AGENTS.md" "$OPENCODE_DIR/AGENTS.md" "AGENTS.md"
# Note: ~/.agents/AGENTS.md is managed by occams-agentic bootstrap.sh.
_preserve_bundled_config "model-profile.jsonc"

# ── Set preset in config files ───────────────────────────────────
if [[ -n "${PRESET:-}" ]]; then
  # Update oh-my-opencode-slim.json (preset + council.default_preset)
  if [[ -f "$OPENCODE_DIR/oh-my-opencode-slim.json" ]]; then
    if [[ "$SLIM_CONFIG_PREEXISTED" -eq 0 ]]; then
      jq --arg p "$PRESET" '.preset = $p | .council.default_preset = $p' \
        "$OPENCODE_DIR/oh-my-opencode-slim.json" > /tmp/oc-slim-$$.json \
        && mv /tmp/oc-slim-$$.json "$OPENCODE_DIR/oh-my-opencode-slim.json"
      echo -e "  ${GREEN}✓${RESET} preset set to '$PRESET' in oh-my-opencode-slim.json"
    else
      echo -e "  ${YELLOW}⊙${RESET} existing oh-my-opencode-slim.json preserved; preset unchanged"
    fi
  fi

  # Update model-profile.jsonc (sed preserves JSONC comments)
  if [[ -f "$OPENCODE_DIR/model-profile.jsonc" ]]; then
    if [[ "$PROFILE_CONFIG_PREEXISTED" -eq 0 ]]; then
      sed -i 's/"preset": "[^"]*"/"preset": "'"$PRESET"'"/' "$OPENCODE_DIR/model-profile.jsonc"
      echo -e "  ${GREEN}✓${RESET} preset set to '$PRESET' in model-profile.jsonc"
    else
      echo -e "  ${YELLOW}⊙${RESET} existing model-profile.jsonc preserved; preset unchanged"
    fi
  fi
fi

# ── Z.AI MCP injection ───────────────────────────────────────────────
if [[ "$ENABLE_ZAI_MCPS" -eq 1 && -n "$ZAI_KEY" && -f "$OPENCODE_DIR/opencode.json" ]]; then
  if [[ "$OPENCODE_CONFIG_PREEXISTED" -eq 1 ]]; then
    echo -e "  ${YELLOW}⊙${RESET} existing opencode.json preserved; merge Z.AI MCPs manually"
  else
    jq '
    .mcp.zai_vision = {
      "type": "local",
      "command": ["npx", "-y", "@z_ai/mcp-server"],
      "environment": { "Z_AI_API_KEY": "{env:Z_AI_API_KEY}", "Z_AI_MODE": "ZAI" },
      "enabled": true,
      "timeout": 600000
    } |
    .mcp["web-search-prime"] = {
      "type": "remote",
      "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
      "headers": { "Authorization": "Bearer {env:Z_AI_API_KEY}" },
      "enabled": true,
      "timeout": 60000
    }
    ' "$OPENCODE_DIR/opencode.json" > /tmp/oc-json-$$.json \
      && mv /tmp/oc-json-$$.json "$OPENCODE_DIR/opencode.json"
    echo -e "  ${GREEN}✓${RESET} Z.AI MCPs added to opencode.json (key via {env:Z_AI_API_KEY} placeholder)"
  fi
fi

# ── Wiki (managed by occams-agentic) ──────────────────────────────────
if [[ -f "$AGENTS_DIR/AGENTS.md" ]]; then
  echo -e "  ${GREEN}✓${RESET} occams-agentic framework detected (wiki via bootstrap.sh)"
else
  echo -e "  ${YELLOW}⚠${RESET} occams-agentic not found at $AGENTS_DIR"
  echo -e "  ${DIM}  Install it first: git clone occams-agentic && ./bin/bootstrap.sh${RESET}"
fi

# ── Install local skills ─────────────────────────────────────────────
echo ""
echo -e "${BOLD}Installing local skills...${RESET}"
SKILLS_DIR="$OPENCODE_DIR/skills"
mkdir -p "$SKILLS_DIR"

for skill in codemap simplify clonedeps; do
  if [[ -d "$REPO_ROOT/skills/$skill" ]]; then
    if [[ ! -d "$SKILLS_DIR/$skill" ]]; then
      cp -r "$REPO_ROOT/skills/$skill" "$SKILLS_DIR/$skill"
      echo -e "  ${GREEN}✓${RESET} $skill skill installed"
    else
      echo -e "  ${DIM}$skill already installed (skipped)${RESET}"
    fi
  fi
done

# ── Install obsidian-skills plugin ───────────────────────────────────
echo ""
echo -e "${BOLD}Installing obsidian-skills plugin...${RESET}"
OBSIDIAN_SKILLS_DIR="$HOME/.opencode/skills"
mkdir -p "$OBSIDIAN_SKILLS_DIR"
if [[ ! -d "$OBSIDIAN_SKILLS_DIR/obsidian-skills" ]]; then
  if command -v git &>/dev/null; then
    git clone https://github.com/kepano/obsidian-skills "$OBSIDIAN_SKILLS_DIR/obsidian-skills"
    echo -e "  ${GREEN}✓${RESET} obsidian-skills cloned"
  else
    echo -e "  ${YELLOW}⚠${RESET} git not found. Clone https://github.com/kepano/obsidian-skills manually to $OBSIDIAN_SKILLS_DIR/obsidian-skills"
  fi
else
  echo -e "  ${DIM}obsidian-skills already installed (skipped)${RESET}"
fi

# ── Install oh-my-opencode-slim ──────────────────────────────────────
echo ""
echo -e "${BOLD}Installing oh-my-opencode-slim plugin...${RESET}"
(
  cd "$OPENCODE_DIR"
  if command -v bun &>/dev/null; then
    if bun install oh-my-opencode-slim; then
      echo -e "  ${GREEN}✓${RESET} Installed via bun"
    else
      echo -e "  ${YELLOW}⚠${RESET} bun install failed — install oh-my-opencode-slim manually"
    fi
  elif command -v npm &>/dev/null; then
    if npm install oh-my-opencode-slim; then
      echo -e "  ${GREEN}✓${RESET} Installed via npm"
    else
      echo -e "  ${YELLOW}⚠${RESET} npm install failed — install oh-my-opencode-slim manually"
    fi
  else
    echo -e "  ${YELLOW}⚠${RESET} Neither bun nor npm found. Install oh-my-opencode-slim manually."
  fi
)

# ── Optional CLIs: defuddle, agent-browser ───────────────────────────
_install_npm_cli() {
  local pkg="$1"
  local bin="$2"
  if command -v bun &>/dev/null; then
    (cd "$OPENCODE_DIR" && bun install "$pkg" &>/dev/null) && \
      ln -sf "$OPENCODE_DIR/node_modules/.bin/$bin" "$HOME/.local/bin/$bin" 2>/dev/null && \
      echo -e "  ${GREEN}✓${RESET} $bin installed (bun)" && return 0
  fi
  if command -v npm &>/dev/null; then
    (cd "$OPENCODE_DIR" && npm install "$pkg" &>/dev/null) && \
      ln -sf "$OPENCODE_DIR/node_modules/.bin/$bin" "$HOME/.local/bin/$bin" 2>/dev/null && \
      echo -e "  ${GREEN}✓${RESET} $bin installed (npm)" && return 0
  fi
  echo -e "  ${YELLOW}⚠${RESET} $bin: no package manager found"
  return 1
}

if [[ "$INSTALL_DEFUDDLE" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Installing defuddle...${RESET}"
  _install_npm_cli "defuddle" "defuddle" || true
fi

if [[ "$INSTALL_AGENT_BROWSER" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Installing agent-browser...${RESET}"
  _install_npm_cli "agent-browser" "agent-browser" || true
fi

# ── Install Obsidian ─────────────────────────────────────────────────
if [[ "$INSTALL_OBSIDIAN" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Obsidian (wiki viewer/editor)${RESET}"
  _obsidian_installed() {
    command -v obsidian &>/dev/null && return 0
    [[ -f /Applications/Obsidian.app/Contents/MacOS/Obsidian ]] && return 0
    [[ -f "${XDG_BIN_HOME:-$HOME/.local/bin}/Obsidian.AppImage" ]] && return 0
    return 1
  }
  if _obsidian_installed; then
    echo -e "  ${DIM}Already installed (skipped)${RESET}"
  else
    echo -e "  ${YELLOW}Not found. Install from https://obsidian.md${RESET}"
    if [[ "$(uname -s)" == "Darwin" ]]; then
      echo -e "  ${DIM}macOS: brew install --cask obsidian${RESET}"
    elif grep -qi microsoft /proc/version 2>/dev/null; then
      echo -e "  ${DIM}WSL: download from https://obsidian.md and install on Windows${RESET}"
    else
      echo -e "  ${DIM}Linux: flatpak install flathub md.obsidian.Obsidian${RESET}"
      echo -e "  ${DIM}    or: download AppImage from https://obsidian.md${RESET}"
    fi
    echo -e "  ${DIM}Then open ~/.agents/wiki/ as a vault${RESET}"
  fi
  unset -f _obsidian_installed 2>/dev/null || true
fi

# ── Cron setup ───────────────────────────────────────────────────────
if [[ "$SETUP_CRON" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Setting up weekly cron job...${RESET}"
  _CRON_CMD="0 0 * * 0 $OPENCODE_DIR/scripts/cleanup-logs.sh"
  if command -v crontab &>/dev/null; then
    if crontab -l 2>/dev/null | grep -qF "cleanup-logs.sh"; then
      echo -e "  ${DIM}Cron job already exists (skipped)${RESET}"
    else
      (crontab -l 2>/dev/null; echo "$_CRON_CMD") | crontab -
      echo -e "  ${GREEN}✓${RESET} Weekly cron job added"
    fi
  else
    echo -e "  ${YELLOW}⚠${RESET} crontab not found. Add manually:"
    echo "    $_CRON_CMD"
  fi
  unset _CRON_CMD
fi

# ── PATH setup ───────────────────────────────────────────────────────
if [[ "$SETUP_PATH" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Setting up PATH...${RESET}"
  _PATH_EXPORT='export PATH="$HOME/.config/opencode/bin:$PATH"'
  for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [[ -f "$rc" ]]; then
      if grep -qF "$HOME/.config/opencode/bin" "$rc"; then
        echo -e "  ${DIM}Already in $rc (skipped)${RESET}"
      else
        echo "$_PATH_EXPORT" >> "$rc"
        echo -e "  ${GREEN}✓${RESET} Added to $rc"
      fi
    fi
  done
  unset _PATH_EXPORT
fi

# ── Secrets setup ────────────────────────────────────────────────────
if [[ "$SETUP_SECRETS" -eq 1 ]]; then
  echo ""
  echo -e "${BOLD}Setting up API secrets...${RESET}"

  # Build secrets file content
  _secrets=""
  _prompt_for_key() {
    local var_name="$1"
    local display_name="$2"
    local key_value=""
    _ask_hidden "  $display_name API key (Enter to skip): " key_value
    if [[ -n "$key_value" ]]; then
      _secrets="${_secrets}export $var_name=\"$key_value\"\n"
    fi
  }

  if [[ "$UNATTENDED" -eq 1 ]]; then
    # In unattended mode, use env vars directly
    [[ -n "${OCCAM_OPENROUTER_KEY:-}" ]] && _secrets="${_secrets}export OPENROUTER_API_KEY=\"$OCCAM_OPENROUTER_KEY\"\n"
    [[ -n "${OCCAM_DEEPSEEK_KEY:-}" ]]   && _secrets="${_secrets}export DEEPSEEK_API_KEY=\"$OCCAM_DEEPSEEK_KEY\"\n"
    [[ -n "${OCCAM_ANTHROPIC_KEY:-}" ]]  && _secrets="${_secrets}export ANTHROPIC_API_KEY=\"$OCCAM_ANTHROPIC_KEY\"\n"
    [[ -n "${OCCAM_KIMI_KEY:-}" ]]       && _secrets="${_secrets}export KIMI_API_KEY=\"$OCCAM_KIMI_KEY\"\n"
    [[ -n "$ZAI_KEY" ]]                  && _secrets="${_secrets}export Z_AI_API_KEY=\"$ZAI_KEY\"\n"
    [[ -n "${OCCAM_HF_TOKEN:-}" ]]       && _secrets="${_secrets}export HF_TOKEN=\"$OCCAM_HF_TOKEN\"\n"
    [[ -n "${OCCAM_EXA_API_KEY:-}" ]]    && _secrets="${_secrets}export EXA_API_KEY=\"$OCCAM_EXA_API_KEY\"\n"
  else
    # Interactive mode: prompt for each selected provider
    if [[ "$PROVIDERS" == *"openrouter"* ]]; then
      _prompt_for_key "OPENROUTER_API_KEY" "OpenRouter"
    fi
    if [[ "$PROVIDERS" == *"deepseek"* ]]; then
      _prompt_for_key "DEEPSEEK_API_KEY" "DeepSeek"
    fi
    if [[ "$PROVIDERS" == *"anthropic"* ]]; then
      _prompt_for_key "ANTHROPIC_API_KEY" "Anthropic"
    fi
    if [[ "$PROVIDERS" == *"zai"* ]]; then
      _prompt_for_key "Z_AI_API_KEY" "Z.AI"
    fi
    if [[ "$PROVIDERS" == *"kimi"* ]]; then
      _prompt_for_key "KIMI_API_KEY" "Kimi"
    fi
    # Optional keys
    _opt_hf=""
    read -rp "  HuggingFace token (optional, for model downloads): " _opt_hf < /dev/tty
    [[ -n "$_opt_hf" ]] && _secrets="${_secrets}export HF_TOKEN=\"$_opt_hf\"\n"
    _opt_exa=""
    read -rp "  Exa API key (optional, for websearch quotas): " _opt_exa < /dev/tty
    [[ -n "$_opt_exa" ]] && _secrets="${_secrets}export EXA_API_KEY=\"$_opt_exa\"\n"
  fi

  if [[ -n "$_secrets" ]]; then
    # Write secrets file (never overwrite existing — append new vars)
    if [[ -f "$SECRETS_FILE" ]]; then
      # Append only new variables
      while IFS= read -r line; do
        if [[ -n "$line" && "$line" == export\ * ]]; then
          _varname="${line#export }"
          _varname="${_varname%%=*}"
          if ! grep -qF "$_varname=" "$SECRETS_FILE"; then
            printf '%s\n' "$line" >> "$SECRETS_FILE"
          fi
        fi
      done < <(echo -e "$_secrets")
      echo -e "  ${GREEN}✓${RESET} Updated $SECRETS_FILE (new keys appended)"
    else
      echo -e "# Occam's Code — shared API secrets\n# Generated by install.sh\n#\n$_secrets" > "$SECRETS_FILE"
      chmod 600 "$SECRETS_FILE"
      echo -e "  ${GREEN}✓${RESET} Created $SECRETS_FILE (mode 600)"
    fi

    # Ensure ~/.profile sources it
    if [[ -f "$HOME/.profile" ]]; then
      if ! grep -qF '.config/secrets/env' "$HOME/.profile"; then
        printf '\n[ -f "$HOME/.config/secrets/env" ] && . "$HOME/.config/secrets/env"\n' >> "$HOME/.profile"
        echo -e "  ${GREEN}✓${RESET} Added source line to ~/.profile"
      else
        echo -e "  ${DIM}~/.profile already sources secrets (skipped)${RESET}"
      fi
    else
      printf '[ -f "$HOME/.config/secrets/env" ] && . "$HOME/.config/secrets/env"\n' > "$HOME/.profile"
      echo -e "  ${GREEN}✓${RESET} Created ~/.profile with secrets source"
    fi
  else
    echo -e "  ${DIM}No secrets provided (skipped)${RESET}"
  fi

  unset _secrets _varname _opt_hf _opt_exa
fi

# ── Post-install verification ────────────────────────────────────────
echo ""
echo -e "${BOLD}Running post-install verification...${RESET}"
if command -v oc &>/dev/null || [[ -x "$OPENCODE_DIR/bin/oc" ]]; then
  if "$OPENCODE_DIR/bin/oc" --doctor 2>/dev/null; then
    echo -e "  ${GREEN}✓${RESET} oc --doctor passed"
  else
    echo -e "  ${YELLOW}⚠${RESET} oc --doctor reported issues (see above)"
  fi
else
  echo -e "  ${YELLOW}⚠${RESET} oc not in PATH yet. After reloading your shell, run: oc --doctor"
fi

# ── Done ─────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}Installation complete!${RESET}"
echo ""
echo "Next steps:"
[[ "$SETUP_PATH" -eq 1 ]] && echo "  1. Reload your shell: source ~/.profile  (or open a new terminal)"
echo "  2. Run: oc --doctor"
echo "  3. Open ~/.agents/wiki/ in Obsidian"
echo "  4. Launch: oc"
echo ""
