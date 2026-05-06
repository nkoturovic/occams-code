#!/usr/bin/env bash
#
# Occam's Code installer
#
# Interactive cross-platform installer for the Occam's Code OpenCode setup.
#
# Usage:
#   ./scripts/install.sh                 # Interactive (recommended)
#   ./scripts/install.sh --unattended    # Use defaults, no prompts
#   ./scripts/install.sh --help          # Show this help
#
# Unattended mode environment variables (override defaults):
#   OCCAM_PRESET=balanced                # balanced|cheap|premium|custom
#   OCCAM_PROVIDERS=openrouter           # csv: openrouter,deepseek,anthropic,zai,kimi
#   OCCAM_ENABLE_ZAI_MCPS=0              # 0|1  inject zai_vision + web-search-prime blocks
#   OCCAM_ZAI_API_KEY=                   # required if OCCAM_ENABLE_ZAI_MCPS=1
#   OCCAM_TRANSCRIBE=skip                # nix|system|openai|skip
#   OCCAM_INSTALL_DEFUDDLE=1             # 0|1
#   OCCAM_INSTALL_AGENT_BROWSER=1        # 0|1
#   OCCAM_INSTALL_OBSIDIAN=1             # 0|1
#   OCCAM_SETUP_CRON=1                   # 0|1
#   OCCAM_SETUP_PATH=1                   # 0|1
#   OCCAM_OPENCODE_DIR=$HOME/.config/opencode
#   OCCAM_WIKI_DIR=$HOME/wiki
#
# Defaults are tuned for the most common case: an OpenRouter-only user.
# The 'balanced' preset works fully with just an OpenRouter API key.

set -euo pipefail

# ─── Constants & colors ─────────────────────────────────────────
BOLD='\033[1m'; DIM='\033[2m'; GREEN='\033[32m'; YELLOW='\033[33m'
RED='\033[31m'; CYAN='\033[36m'; RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OPENCODE_DIR="${OCCAM_OPENCODE_DIR:-$HOME/.config/opencode}"
WIKI_DIR="${OCCAM_WIKI_DIR:-$HOME/wiki}"
SKILLS_DIR="$OPENCODE_DIR/skills"
OBSIDIAN_SKILLS_DIR="$HOME/.opencode/skills"

UNATTENDED=0
case "${1:-}" in
    --help|-h)
        sed -n '3,28p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
        exit 0 ;;
    --unattended) UNATTENDED=1 ;;
    "") : ;;
    *) echo "Unknown flag: $1 (use --help)" >&2; exit 1 ;;
esac

# ─── Tiny helpers ───────────────────────────────────────────────
log()      { printf '%b\n' "$*"; }
ok()       { printf "  ${GREEN}✓${RESET} %b\n" "$*"; }
warn()     { printf "  ${YELLOW}⚠${RESET} %b\n" "$*"; }
err()      { printf "  ${RED}✗${RESET} %b\n" "$*" >&2; }
section()  { printf "\n${BOLD}%b${RESET}\n" "$*"; }
hr()       { printf "${DIM}%s${RESET}\n" "─────────────────────────────────────────"; }

ask() {
    # ask "Question?" "default" → returns user input or default
    local prompt="$1" default="${2:-}" answer
    if [[ "$UNATTENDED" == 1 ]] || [[ ! -t 0 ]]; then
        printf '%s' "$default"; return
    fi
    if [[ -n "$default" ]]; then
        read -r -p "$(printf '%b [%b]: ' "$prompt" "$default")" answer < /dev/tty
    else
        read -r -p "$(printf '%b: ' "$prompt")" answer < /dev/tty
    fi
    printf '%s' "${answer:-$default}"
}

ask_yn() {
    # ask_yn "Question?" "Y" → returns 0 (yes) or 1 (no); default Y or N
    local q="$1" def="${2:-N}" hint ans
    [[ "$def" =~ ^[Yy]$ ]] && hint="[Y/n]" || hint="[y/N]"
    if [[ "$UNATTENDED" == 1 ]] || [[ ! -t 0 ]]; then
        [[ "$def" =~ ^[Yy]$ ]] && return 0 || return 1
    fi
    read -r -p "$(printf '%b %s: ' "$q" "$hint")" ans < /dev/tty
    ans="${ans:-$def}"
    [[ "$ans" =~ ^[Yy]([Ee][Ss])?$ ]]
}

is_in_csv() {
    # is_in_csv "needle" "a,b,c" → 0 if found, 1 otherwise
    local needle="$1" csv="$2" item
    IFS=',' read -ra arr <<< "$csv"
    for item in "${arr[@]}"; do [[ "$item" == "$needle" ]] && return 0; done
    return 1
}

# ─── Banner ─────────────────────────────────────────────────────
log ""
log "${BOLD}${CYAN}  ▄  Occam's Code  ▄${RESET}"
log "${DIM}  ─────────────────${RESET}"
log "${DIM}  OpenCode setup sharpened by Occam's Razor${RESET}"
log ""
[[ "$UNATTENDED" == 1 ]] && log "${YELLOW}  (unattended mode — using defaults + env vars)${RESET}\n"

# ─── Platform detection ─────────────────────────────────────────
PLATFORM="$(uname -s)"
ARCH="$(uname -m)"
IS_WSL=0
grep -qi microsoft /proc/version 2>/dev/null && IS_WSL=1

case "$PLATFORM" in
    Linux)
        if [[ "$IS_WSL" == 1 ]]; then PLATFORM_LABEL="WSL ($ARCH)"; else PLATFORM_LABEL="Linux ($ARCH)"; fi ;;
    Darwin)  PLATFORM_LABEL="macOS ($ARCH)" ;;
    *)       PLATFORM_LABEL="$PLATFORM ($ARCH) — UNSUPPORTED"; err "Only Linux, WSL, and macOS are supported."; exit 1 ;;
esac
log "  Platform: ${GREEN}$PLATFORM_LABEL${RESET}"
log "  Source:   ${GREEN}$REPO_ROOT${RESET}"
log "  Target:   ${GREEN}$OPENCODE_DIR${RESET}"
log "  Wiki:     ${GREEN}$WIKI_DIR${RESET}"

# ─── Bash version gate ──────────────────────────────────────────
# Installer itself works with bash 3.2; the produced bin/oc requires 4+.
if [[ "${BASH_VERSINFO[0]:-0}" -lt 4 ]]; then
    log ""
    warn "Detected bash ${BASH_VERSION}. The installer will succeed,"
    warn "but ${BOLD}bin/oc requires bash 4.0+${RESET}."
    if [[ "$PLATFORM" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            log "    ${DIM}Tip: 'brew install bash', then run oc with /opt/homebrew/bin/bash${RESET}"
        else
            log "    ${DIM}Tip: install Homebrew, then 'brew install bash'${RESET}"
        fi
    fi
fi

# ─── Required dependencies ──────────────────────────────────────
section "Checking required dependencies"
DEPS_OK=1
for cmd in python3 jq curl git; do
    if command -v "$cmd" &>/dev/null; then ok "$cmd: $(command -v "$cmd")"
    else err "$cmd: not found"; DEPS_OK=0; fi
done
if [[ "$DEPS_OK" != 1 ]]; then
    err "Missing required dependencies. Install them and re-run."
    case "$PLATFORM" in
        Linux)  log "  ${DIM}sudo apt install python3 jq curl git    # Debian/Ubuntu${RESET}"
                log "  ${DIM}sudo dnf install python3 jq curl git    # Fedora${RESET}"
                log "  ${DIM}sudo pacman -S python3 jq curl git      # Arch${RESET}" ;;
        Darwin) log "  ${DIM}brew install python3 jq curl git${RESET}" ;;
    esac
    exit 1
fi

# Optional but recommended
for cmd in npm bun fzf node; do
    if command -v "$cmd" &>/dev/null; then ok "$cmd: $(command -v "$cmd") ${DIM}(optional)${RESET}"
    else warn "$cmd: not found ${DIM}(optional — see notes below)${RESET}"; fi
done

# ─── Q1: API providers ──────────────────────────────────────────
section "1. API providers"
log "${DIM}  Which API provider(s) will you use? Multiple allowed.${RESET}"
log "${DIM}  OpenRouter is recommended for most users (400+ models, single API key, pay-per-token).${RESET}"
log ""

PROVIDERS_DEFAULT="${OCCAM_PROVIDERS:-openrouter}"
log "  ${GREEN}1.${RESET} OpenRouter   ${DIM}— 400+ models incl. GLM, Qwen, Gemini, Sonnet, Kimi   (recommended)${RESET}"
log "  ${GREEN}2.${RESET} DeepSeek     ${DIM}— direct API for V4 Pro / V4 Flash (best for reasoning)${RESET}"
log "  ${GREEN}3.${RESET} Anthropic    ${DIM}— direct API for Claude Opus / Sonnet (premium preset)${RESET}"
log "  ${GREEN}4.${RESET} Z.AI         ${DIM}— GLM-5.1 + zai_vision MCP (subscription, opt-in)${RESET}"
log "  ${GREEN}5.${RESET} Kimi         ${DIM}— Kimi for Coding K2.6 (subscription, custom preset)${RESET}"
log ""
log "${DIM}  Enter comma-separated numbers (e.g., '1,2'). Default: 1 (OpenRouter only).${RESET}"

if [[ "$UNATTENDED" == 1 ]]; then
    PROVIDERS="$PROVIDERS_DEFAULT"
else
    PROVIDERS_INPUT="$(ask "  Choice" "1")"
    PROVIDERS=""
    IFS=',' read -ra arr <<< "$PROVIDERS_INPUT"
    for n in "${arr[@]}"; do
        n="${n// /}"
        case "$n" in
            1) PROVIDERS="${PROVIDERS},openrouter" ;;
            2) PROVIDERS="${PROVIDERS},deepseek" ;;
            3) PROVIDERS="${PROVIDERS},anthropic" ;;
            4) PROVIDERS="${PROVIDERS},zai" ;;
            5) PROVIDERS="${PROVIDERS},kimi" ;;
        esac
    done
    PROVIDERS="${PROVIDERS#,}"
    [[ -z "$PROVIDERS" ]] && PROVIDERS="openrouter"
fi
ok "Providers: ${BOLD}$PROVIDERS${RESET}"

# ─── Q2: Default preset ─────────────────────────────────────────
section "2. Default preset"
log "${DIM}  Which preset should oc use by default? (You can override per-project later.)${RESET}"
log ""

# Recommend preset based on selected providers
RECOMMENDED_PRESET="balanced"
if is_in_csv "anthropic" "$PROVIDERS"; then
    RECOMMENDED_PRESET="premium"
elif is_in_csv "kimi" "$PROVIDERS" && is_in_csv "zai" "$PROVIDERS"; then
    RECOMMENDED_PRESET="custom"
fi

log "  ${GREEN}1.${RESET} balanced  ${DIM}— OpenRouter-only OOB ($([[ "$RECOMMENDED_PRESET" == "balanced" ]] && echo "recommended for you"))${RESET}"
log "  ${GREEN}2.${RESET} cheap     ${DIM}— Free / cheapest models (incl. Nemotron free tier)${RESET}"
log "  ${GREEN}3.${RESET} premium   ${DIM}— Claude Opus orchestrator + oracle ($([[ "$RECOMMENDED_PRESET" == "premium" ]] && echo "recommended" || echo "needs Anthropic key"))${RESET}"
log "  ${GREEN}4.${RESET} custom    ${DIM}— DeepSeek + Kimi + Z.AI ($([[ "$RECOMMENDED_PRESET" == "custom" ]] && echo "recommended" || echo "needs all 3 subscriptions"))${RESET}"
log ""

PRESET_DEFAULT="${OCCAM_PRESET:-$RECOMMENDED_PRESET}"
case "$PRESET_DEFAULT" in
    balanced) PRESET_NUM=1 ;; cheap) PRESET_NUM=2 ;;
    premium) PRESET_NUM=3 ;;  custom) PRESET_NUM=4 ;;
    *) PRESET_NUM=1; PRESET_DEFAULT=balanced ;;
esac

if [[ "$UNATTENDED" == 1 ]]; then
    PRESET="$PRESET_DEFAULT"
else
    PRESET_INPUT="$(ask "  Choice" "$PRESET_NUM")"
    case "$PRESET_INPUT" in
        1|balanced) PRESET=balanced ;;
        2|cheap)    PRESET=cheap    ;;
        3|premium)  PRESET=premium  ;;
        4|custom)   PRESET=custom   ;;
        *) PRESET="$PRESET_DEFAULT" ;;
    esac
fi
ok "Preset: ${BOLD}$PRESET${RESET}"

# ─── Q3: Z.AI MCPs (only if Z.AI selected) ──────────────────────
ENABLE_ZAI_MCPS=0
ZAI_API_KEY=""
if is_in_csv "zai" "$PROVIDERS"; then
    section "3. Z.AI MCPs (zai_vision + web-search-prime)"
    log "${DIM}  These provide image analysis (OCR, diagrams) and Z.AI web search.${RESET}"
    log "${DIM}  Both are redundant with the multimodal observer agent + Exa websearch (built-in).${RESET}"
    log "${DIM}  Enable only if you specifically want Z.AI's tooling on top.${RESET}"
    log ""
    if [[ "${OCCAM_ENABLE_ZAI_MCPS:-}" == "1" ]] || ask_yn "  Enable Z.AI MCPs?" "N"; then
        ENABLE_ZAI_MCPS=1
        ZAI_API_KEY="${OCCAM_ZAI_API_KEY:-}"
        if [[ -z "$ZAI_API_KEY" && "$UNATTENDED" != 1 ]]; then
            read -r -p "$(printf '  Paste your Z.AI API key (input hidden): ')" -s ZAI_API_KEY < /dev/tty || true
            log ""
        fi
        if [[ -z "$ZAI_API_KEY" ]]; then
            warn "No Z.AI key provided — MCPs will be added with a placeholder. Edit opencode.json later."
            ZAI_API_KEY="YOUR_ZAI_API_KEY"
        fi
        ok "Z.AI MCPs will be injected into opencode.json"
    else
        ok "Z.AI MCPs not added (default)"
    fi
fi

# ─── Q4: Transcription backend ──────────────────────────────────
section "4. Audio/video transcription backend"
log "${DIM}  Used by: scripts/transcribe (lecture-notes pipeline, audio-analysis skill).${RESET}"
log ""
log "  ${GREEN}1.${RESET} nix flake (whisper.cpp via kotur-nixpkgs, GPU/Vulkan)  ${DIM}— Linux/WSL, requires nix${RESET}"
log "  ${GREEN}2.${RESET} system whisper-cpp                                     ${DIM}— brew/apt/dnf, CPU only on most setups${RESET}"
log "  ${GREEN}3.${RESET} OpenAI Whisper API                                     ${DIM}— any platform, ~\$0.006/min, requires OpenAI key${RESET}"
log "  ${GREEN}4.${RESET} Skip                                                   ${DIM}— lecture-notes/audio-analysis skills disabled${RESET}"
log ""

TRANSCRIBE_DEFAULT="${OCCAM_TRANSCRIBE:-skip}"
case "$TRANSCRIBE_DEFAULT" in nix) TR_NUM=1 ;; system) TR_NUM=2 ;; openai) TR_NUM=3 ;; skip|*) TR_NUM=4; TRANSCRIBE_DEFAULT=skip ;; esac

if [[ "$UNATTENDED" == 1 ]]; then
    TRANSCRIBE="$TRANSCRIBE_DEFAULT"
else
    TR_INPUT="$(ask "  Choice" "$TR_NUM")"
    case "$TR_INPUT" in
        1|nix)    TRANSCRIBE=nix    ;;
        2|system) TRANSCRIBE=system ;;
        3|openai) TRANSCRIBE=openai ;;
        4|skip|*) TRANSCRIBE=skip   ;;
    esac
fi
ok "Transcription: ${BOLD}$TRANSCRIBE${RESET}"

# ─── Q5: Optional CLIs ──────────────────────────────────────────
section "5. Optional CLIs"
log "${DIM}  These are referenced by skills/agents but are optional.${RESET}"
log ""

INSTALL_DEFUDDLE=0
if [[ "${OCCAM_INSTALL_DEFUDDLE:-}" == "0" ]]; then :
elif [[ "${OCCAM_INSTALL_DEFUDDLE:-}" == "1" ]] || ask_yn "  Install ${BOLD}defuddle${RESET} (clean markdown from web pages, used by defuddle skill)?" "Y"; then
    INSTALL_DEFUDDLE=1
fi

INSTALL_AGENT_BROWSER=0
if [[ "${OCCAM_INSTALL_AGENT_BROWSER:-}" == "0" ]]; then :
elif [[ "${OCCAM_INSTALL_AGENT_BROWSER:-}" == "1" ]] || ask_yn "  Install ${BOLD}agent-browser${RESET} (browser automation, used by designer agent)?" "Y"; then
    INSTALL_AGENT_BROWSER=1
fi

INSTALL_OBSIDIAN=0
if [[ "${OCCAM_INSTALL_OBSIDIAN:-}" == "0" ]]; then :
elif [[ "${OCCAM_INSTALL_OBSIDIAN:-}" == "1" ]] || ask_yn "  Install ${BOLD}Obsidian${RESET} (visual wiki editor, recommended)?" "Y"; then
    INSTALL_OBSIDIAN=1
fi

# ─── Q6: Cron + PATH ────────────────────────────────────────────
section "6. System integration"

SETUP_CRON=0
if [[ "${OCCAM_SETUP_CRON:-}" == "0" ]]; then :
elif [[ "${OCCAM_SETUP_CRON:-}" == "1" ]] || ask_yn "  Set up weekly log cleanup cron (Sun 03:00, 30-day retention)?" "Y"; then
    SETUP_CRON=1
fi

SETUP_PATH=0
if [[ "${OCCAM_SETUP_PATH:-}" == "0" ]]; then :
elif [[ "${OCCAM_SETUP_PATH:-}" == "1" ]] || ask_yn "  Add 'oc' to your PATH (modifies shell rc)?" "Y"; then
    SETUP_PATH=1
fi

# ─── Confirmation ───────────────────────────────────────────────
section "Summary"
hr
printf "  Platform:        %s\n" "$PLATFORM_LABEL"
printf "  Install path:    %s\n" "$OPENCODE_DIR"
printf "  Wiki path:       %s\n" "$WIKI_DIR"
printf "  Providers:       %s\n" "$PROVIDERS"
printf "  Default preset:  %s\n" "$PRESET"
printf "  Z.AI MCPs:       %s\n" "$([[ $ENABLE_ZAI_MCPS == 1 ]] && echo "enabled" || echo "disabled (opt-in later)")"
printf "  Transcription:   %s\n" "$TRANSCRIBE"
printf "  defuddle:        %s\n" "$([[ $INSTALL_DEFUDDLE == 1 ]] && echo "install" || echo "skip")"
printf "  agent-browser:   %s\n" "$([[ $INSTALL_AGENT_BROWSER == 1 ]] && echo "install" || echo "skip")"
printf "  Obsidian:        %s\n" "$([[ $INSTALL_OBSIDIAN == 1 ]] && echo "install" || echo "skip")"
printf "  Weekly cron:     %s\n" "$([[ $SETUP_CRON == 1 ]] && echo "yes" || echo "no")"
printf "  Add to PATH:     %s\n" "$([[ $SETUP_PATH == 1 ]] && echo "yes" || echo "no")"
hr
log ""

if [[ "$UNATTENDED" != 1 ]]; then
    if ! ask_yn "Proceed with installation?" "Y"; then
        log "  Aborted."; exit 0
    fi
fi

# ═══ EXECUTION ══════════════════════════════════════════════════

# ─── Create directories ─────────────────────────────────────────
section "Creating directories"
mkdir -p "$OPENCODE_DIR"/{bin,scripts,commands,skills}
mkdir -p "$WIKI_DIR"/raw/{articles,papers,repos,docs,forums,assets,_inbox}
mkdir -p "$WIKI_DIR"/wiki/{projects,domain,languages,patterns,concepts,entities,sources,comparisons}
mkdir -p "$OBSIDIAN_SKILLS_DIR"
ok "Directories created"

# ─── Copy configs (skip if already exists) ──────────────────────
section "Copying core files"

cp_safe() {
    # cp_safe SRC DEST [LABEL]
    local src="$1" dest="$2" label="${3:-$2}"
    if [[ ! -f "$src" ]]; then warn "Source missing: $src"; return; fi
    if [[ -f "$dest" ]]; then
        ok "$label ${DIM}(already exists, skipped)${RESET}"
    else
        cp "$src" "$dest" && ok "$label"
    fi
}

# bin/oc (always overwrite — script updates should propagate)
if [[ -f "$REPO_ROOT/bin/oc" ]]; then
    cp "$REPO_ROOT/bin/oc" "$OPENCODE_DIR/bin/oc"
    chmod +x "$OPENCODE_DIR/bin/oc"
    ok "bin/oc"
fi

# Scripts (overwrite — bug fixes should propagate)
if ls "$REPO_ROOT"/scripts/*.py >/dev/null 2>&1; then
    cp "$REPO_ROOT"/scripts/*.py "$OPENCODE_DIR/scripts/"
    ok "scripts/*.py ($(ls "$REPO_ROOT"/scripts/*.py | wc -l) files)"
fi
for s in "$REPO_ROOT"/scripts/*; do
    [[ -f "$s" ]] || continue
    case "$s" in *.py|*/install.sh) continue ;; esac  # skip .py (handled) and self
    sname="$(basename "$s")"
    cp "$s" "$OPENCODE_DIR/scripts/$sname"
    chmod +x "$OPENCODE_DIR/scripts/$sname"
    ok "scripts/$sname"
done

# Commands (overwrite)
if ls "$REPO_ROOT"/commands/*.md >/dev/null 2>&1; then
    cp "$REPO_ROOT"/commands/*.md "$OPENCODE_DIR/commands/"
    ok "commands/*.md ($(ls "$REPO_ROOT"/commands/*.md | wc -l) files)"
fi

# AGENTS.md (skip if exists — user may have customized)
cp_safe "$REPO_ROOT/AGENTS.md" "$OPENCODE_DIR/AGENTS.md" "AGENTS.md"

# model-profile.jsonc (skip if exists — user may have customized model assignments)
cp_safe "$REPO_ROOT/model-profile.jsonc" "$OPENCODE_DIR/model-profile.jsonc" "model-profile.jsonc"

# opencode.json (skip if exists — has provider keys, MCPs)
cp_safe "$REPO_ROOT/config/opencode.json" "$OPENCODE_DIR/opencode.json" "opencode.json"

# oh-my-opencode-slim.json (skip if exists — preset/agent overrides)
cp_safe "$REPO_ROOT/config/oh-my-opencode-slim.json" "$OPENCODE_DIR/oh-my-opencode-slim.json" "oh-my-opencode-slim.json"

# ─── Set selected preset ────────────────────────────────────────
if [[ -f "$OPENCODE_DIR/oh-my-opencode-slim.json" ]] && command -v jq &>/dev/null; then
    tmp="$(mktemp)"
    jq --arg p "$PRESET" '.preset = $p' "$OPENCODE_DIR/oh-my-opencode-slim.json" > "$tmp" \
        && mv "$tmp" "$OPENCODE_DIR/oh-my-opencode-slim.json" \
        && ok "Default preset → $PRESET"
fi

# ─── Inject Z.AI MCPs (if opted in) ─────────────────────────────
if [[ "$ENABLE_ZAI_MCPS" == 1 ]]; then
    section "Injecting Z.AI MCP blocks"
    tmp="$(mktemp)"
    jq --arg key "$ZAI_API_KEY" '
        .mcp.zai_vision = {
            "type": "local",
            "command": ["npx", "-y", "@z_ai/mcp-server"],
            "environment": { "Z_AI_API_KEY": $key, "Z_AI_MODE": "ZAI" },
            "enabled": true,
            "timeout": 600000
        } |
        .mcp["web-search-prime"] = {
            "type": "remote",
            "url": "https://api.z.ai/api/mcp/web_search_prime/mcp",
            "headers": { "Authorization": ("Bearer " + $key) },
            "enabled": true,
            "timeout": 60000
        }
    ' "$OPENCODE_DIR/opencode.json" > "$tmp" && mv "$tmp" "$OPENCODE_DIR/opencode.json"
    ok "zai_vision + web-search-prime added to opencode.json"
fi

# ─── Wiki template ──────────────────────────────────────────────
section "Setting up wiki at $WIKI_DIR"

# Top-level wiki files
for f in AGENTS.md index.md overview.md log.md .gitignore; do
    [[ -f "$REPO_ROOT/wiki/$f" ]] || continue
    if [[ ! -f "$WIKI_DIR/$f" ]]; then
        cp "$REPO_ROOT/wiki/$f" "$WIKI_DIR/$f"
        ok "wiki/$f"
    else
        ok "wiki/$f ${DIM}(exists, skipped)${RESET}"
    fi
done

# .obsidian/ (Obsidian vault metadata)
if [[ -d "$REPO_ROOT/wiki/.obsidian" && ! -d "$WIKI_DIR/.obsidian" ]]; then
    cp -r "$REPO_ROOT/wiki/.obsidian" "$WIKI_DIR/.obsidian"
    ok ".obsidian/ (vault metadata)"
fi

# All concept pages
mkdir -p "$WIKI_DIR/wiki/concepts"
for f in "$REPO_ROOT"/wiki/wiki/concepts/*.md; do
    [[ -f "$f" ]] || continue
    base="$(basename "$f")"
    if [[ ! -f "$WIKI_DIR/wiki/concepts/$base" ]]; then
        cp "$f" "$WIKI_DIR/wiki/concepts/$base"
        ok "wiki/wiki/concepts/$base"
    fi
done

# raw/README.md
mkdir -p "$WIKI_DIR/raw"
if [[ -f "$REPO_ROOT/wiki/raw/README.md" && ! -f "$WIKI_DIR/raw/README.md" ]]; then
    cp "$REPO_ROOT/wiki/raw/README.md" "$WIKI_DIR/raw/README.md"
    ok "raw/README.md"
fi

# Source template
mkdir -p "$WIKI_DIR/wiki/sources"
src_tpl="$REPO_ROOT/wiki/wiki/sources/_template-source-summary.md"
if [[ -f "$src_tpl" && ! -f "$WIKI_DIR/wiki/sources/_template-source-summary.md" ]]; then
    cp "$src_tpl" "$WIKI_DIR/wiki/sources/_template-source-summary.md"
    ok "wiki/wiki/sources/_template-source-summary.md"
fi

# Patterns + languages (any *.md present)
for sub in patterns languages; do
    if [[ -d "$REPO_ROOT/wiki/wiki/$sub" ]]; then
        mkdir -p "$WIKI_DIR/wiki/$sub"
        for f in "$REPO_ROOT"/wiki/wiki/$sub/*.md; do
            [[ -f "$f" ]] || continue
            base="$(basename "$f")"
            [[ -f "$WIKI_DIR/wiki/$sub/$base" ]] && continue
            cp "$f" "$WIKI_DIR/wiki/$sub/$base"
            ok "wiki/wiki/$sub/$base"
        done
    fi
done

# .gitkeep in empty subdirs (portable replacement for {x,y,z}/.gitkeep)
find "$WIKI_DIR" -type d -empty -exec sh -c 'touch "$1/.gitkeep"' _ {} \; 2>/dev/null || true

# ─── Local skills (codemap, simplify, audio/video/lecture) ──────
section "Installing local skills"
for skill in codemap simplify audio-analysis video-analysis lecture-notes; do
    src="$REPO_ROOT/skills/$skill"
    dest="$SKILLS_DIR/$skill"
    [[ -d "$src" ]] || continue
    if [[ -d "$dest" ]]; then
        ok "$skill ${DIM}(exists, skipped)${RESET}"
    else
        cp -r "$src" "$dest"
        ok "$skill"
    fi
done

# ─── Obsidian-skills bundle ─────────────────────────────────────
section "Installing obsidian-skills bundle"
if [[ -d "$OBSIDIAN_SKILLS_DIR/obsidian-skills" ]]; then
    ok "obsidian-skills ${DIM}(exists, skipped)${RESET}"
elif command -v git &>/dev/null; then
    if git clone --depth=1 https://github.com/kepano/obsidian-skills "$OBSIDIAN_SKILLS_DIR/obsidian-skills" 2>/dev/null; then
        ok "obsidian-skills cloned to $OBSIDIAN_SKILLS_DIR/"
    else
        warn "obsidian-skills clone failed — skill set incomplete"
    fi
else
    warn "git not found — obsidian-skills not installed"
fi

# ─── oh-my-opencode-slim plugin ─────────────────────────────────
section "Installing oh-my-opencode-slim plugin"
(
    cd "$OPENCODE_DIR"
    if command -v bun &>/dev/null; then
        bun install oh-my-opencode-slim 2>&1 | tail -3 && ok "Installed via bun"
    elif command -v npm &>/dev/null; then
        npm install oh-my-opencode-slim 2>&1 | tail -3 && ok "Installed via npm"
    else
        warn "Neither bun nor npm — install plugin manually:"
        log "    cd $OPENCODE_DIR && npm install oh-my-opencode-slim"
    fi
)

# ─── Optional CLIs ──────────────────────────────────────────────
if [[ "$INSTALL_DEFUDDLE" == 1 ]]; then
    section "Installing defuddle"
    if command -v defuddle &>/dev/null; then
        ok "defuddle: $(defuddle --version 2>&1 | head -1) ${DIM}(already installed)${RESET}"
    elif command -v npm &>/dev/null; then
        npm install -g defuddle 2>&1 | tail -1
        if command -v defuddle &>/dev/null; then
            ok "defuddle installed"
        else
            # npm prefix may not be in PATH
            NPM_BIN="$(npm config get prefix 2>/dev/null)/bin"
            if [[ -x "$NPM_BIN/defuddle" ]]; then
                mkdir -p "$HOME/.local/bin"
                ln -sf "$NPM_BIN/defuddle" "$HOME/.local/bin/defuddle"
                ok "defuddle symlinked to ~/.local/bin/ (npm prefix not in PATH)"
            else
                warn "defuddle install unclear — check 'which defuddle'"
            fi
        fi
    else
        warn "npm not available — install manually: npm install -g defuddle"
    fi
fi

if [[ "$INSTALL_AGENT_BROWSER" == 1 ]]; then
    section "Installing agent-browser"
    if command -v agent-browser &>/dev/null; then
        ok "agent-browser ${DIM}(already installed)${RESET}"
    elif command -v npm &>/dev/null; then
        npm install -g agent-browser 2>&1 | tail -1 && ok "agent-browser installed"
    else
        warn "npm not available — install manually: npm install -g agent-browser"
    fi
fi

# ─── Transcription backend ──────────────────────────────────────
case "$TRANSCRIBE" in
    nix)
        section "Setting up transcription (nix flake)"
        if command -v nix &>/dev/null; then
            ok "nix found — transcribe script will use github:nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan on first run"
            log "    ${DIM}(model auto-downloaded to ~/.local/share/opencode/models/whisper/ on first use)${RESET}"
        else
            warn "nix not found. Install nix first: https://nixos.org/download.html"
            warn "Then 'transcribe' will work automatically."
        fi
        ;;
    system)
        section "Setting up transcription (system whisper-cpp)"
        if command -v whisper-cli &>/dev/null; then
            ok "whisper-cli already present: $(command -v whisper-cli)"
        else
            log "  Install whisper.cpp via your package manager:"
            case "$PLATFORM" in
                Darwin) log "    ${DIM}brew install whisper-cpp${RESET}" ;;
                Linux)
                    log "    ${DIM}# Debian/Ubuntu: build from source (no apt package yet)${RESET}"
                    log "    ${DIM}#   git clone https://github.com/ggerganov/whisper.cpp${RESET}"
                    log "    ${DIM}#   cd whisper.cpp && make${RESET}"
                    log "    ${DIM}# Fedora: dnf install whisper-cpp${RESET}"
                    log "    ${DIM}# Arch:   pacman -S whisper.cpp${RESET}" ;;
            esac
            warn "Then edit $OPENCODE_DIR/scripts/transcribe to use 'whisper-cli' instead of 'nix run'."
        fi
        ;;
    openai)
        section "Setting up transcription (OpenAI Whisper API)"
        warn "transcribe script currently uses whisper.cpp via nix."
        warn "For OpenAI API: replace the 'exec nix run ...' line with a curl to https://api.openai.com/v1/audio/transcriptions"
        log "    ${DIM}Quick reference: https://platform.openai.com/docs/api-reference/audio${RESET}"
        ;;
    skip)
        section "Transcription skipped"
        log "  ${DIM}lecture-notes and audio-analysis skills will require manual setup.${RESET}"
        ;;
esac

# ─── Obsidian install ───────────────────────────────────────────
if [[ "$INSTALL_OBSIDIAN" == 1 ]]; then
    section "Installing Obsidian"
    _obsidian_installed() {
        command -v obsidian &>/dev/null && return 0
        [[ -f /Applications/Obsidian.app/Contents/MacOS/Obsidian ]] && return 0
        [[ -f "${XDG_BIN_HOME:-$HOME/.local/bin}/Obsidian.AppImage" ]] && return 0
        return 1
    }
    if _obsidian_installed; then
        ok "Obsidian already installed"
    elif [[ "$PLATFORM" == "Darwin" ]] && command -v brew &>/dev/null; then
        brew install --cask obsidian 2>&1 | tail -3 && ok "Installed via Homebrew"
    elif [[ "$IS_WSL" == 1 ]]; then
        warn "WSL detected — install Obsidian on Windows side: https://obsidian.md"
    elif [[ "$PLATFORM" == "Linux" ]] && command -v flatpak &>/dev/null; then
        flatpak install -y flathub md.obsidian.Obsidian 2>&1 | tail -3 && ok "Installed via Flatpak"
    elif [[ "$PLATFORM" == "Linux" ]]; then
        # AppImage download
        TAG=$(curl -fsSI https://github.com/obsidianmd/obsidian-releases/releases/latest 2>/dev/null \
            | grep -i '^location:' | tr -d '\r' | sed 's|.*/tag/||' || true)
        if [[ -n "$TAG" ]]; then
            VER="${TAG#v}"
            case "$ARCH" in
                x86_64|amd64) AIMG="Obsidian-$VER.AppImage" ;;
                aarch64|arm64) AIMG="Obsidian-$VER-arm64.AppImage" ;;
                *) AIMG="" ;;
            esac
            if [[ -n "$AIMG" ]]; then
                INSTALL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
                mkdir -p "$INSTALL_BIN"
                if curl -fsSL -o "$INSTALL_BIN/Obsidian.AppImage" "https://github.com/obsidianmd/obsidian-releases/releases/download/$TAG/$AIMG"; then
                    chmod +x "$INSTALL_BIN/Obsidian.AppImage"
                    ok "Installed: $INSTALL_BIN/Obsidian.AppImage"
                else
                    warn "Download failed — get it from https://obsidian.md"
                fi
            else
                warn "Unsupported architecture: $ARCH"
            fi
        fi
    else
        warn "Could not auto-install Obsidian — get it from https://obsidian.md"
    fi
fi

# ─── Cron setup ─────────────────────────────────────────────────
if [[ "$SETUP_CRON" == 1 ]]; then
    section "Setting up weekly log cleanup cron"
    CRON_LINE="0 3 * * 0 $OPENCODE_DIR/scripts/cleanup-logs.sh"
    if command -v crontab &>/dev/null; then
        if crontab -l 2>/dev/null | grep -F -q "cleanup-logs.sh"; then
            ok "cron entry already exists"
        else
            (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
            ok "Added: $CRON_LINE"
        fi
    else
        warn "crontab not available — run manually weekly: $OPENCODE_DIR/scripts/cleanup-logs.sh"
    fi
fi

# ─── PATH setup ─────────────────────────────────────────────────
if [[ "$SETUP_PATH" == 1 ]]; then
    section "Adding 'oc' to PATH"
    SHELL_RC=""
    [[ -f "$HOME/.zshrc"  ]] && SHELL_RC="$HOME/.zshrc"
    [[ -f "$HOME/.bashrc" ]] && SHELL_RC="${SHELL_RC:-$HOME/.bashrc}"
    [[ "$PLATFORM" == "Darwin" && -f "$HOME/.zshrc" ]] && SHELL_RC="$HOME/.zshrc"
    if [[ -z "$SHELL_RC" ]]; then
        SHELL_RC="$HOME/.bashrc"
        touch "$SHELL_RC"
    fi
    PATH_LINE='export PATH="$HOME/.config/opencode/bin:$PATH"'
    if grep -F -q ".config/opencode/bin" "$SHELL_RC" 2>/dev/null; then
        ok "PATH already set in $SHELL_RC"
    else
        printf '\n# Occam'\''s Code launcher\n%s\n' "$PATH_LINE" >> "$SHELL_RC"
        ok "Appended to $SHELL_RC — restart shell or 'source $SHELL_RC' to activate"
    fi
fi

# ═══ POST-INSTALL ═══════════════════════════════════════════════
section "Verification"
[[ -f "$OPENCODE_DIR/bin/oc" ]] && ok "bin/oc present" || err "bin/oc MISSING"
[[ -f "$OPENCODE_DIR/oh-my-opencode-slim.json" ]] && ok "oh-my-opencode-slim.json present" || err "slim.json MISSING"
[[ -f "$OPENCODE_DIR/opencode.json" ]] && ok "opencode.json present" || err "opencode.json MISSING"
[[ -f "$OPENCODE_DIR/AGENTS.md" ]] && ok "AGENTS.md present" || err "AGENTS.md MISSING"
[[ -f "$WIKI_DIR/index.md" ]] && ok "wiki/index.md present" || err "wiki/index.md MISSING"
[[ -d "$WIKI_DIR/wiki/concepts" ]] && ok "wiki/wiki/concepts/ ($(find "$WIKI_DIR/wiki/concepts" -name '*.md' 2>/dev/null | wc -l) pages)"

# JSON validity
if jq empty "$OPENCODE_DIR/opencode.json" 2>/dev/null && jq empty "$OPENCODE_DIR/oh-my-opencode-slim.json" 2>/dev/null; then
    ok "JSON files valid"
else
    err "Some JSON files have syntax errors"
fi

# ─── Done + next steps ──────────────────────────────────────────
log ""
hr
log "${GREEN}${BOLD}  Installation complete!${RESET}"
hr
log ""
log "${BOLD}Next steps:${RESET}"
[[ "$SETUP_PATH" != 1 ]] && \
    log "  ${CYAN}1.${RESET} Add to PATH: ${DIM}echo 'export PATH=\"\$HOME/.config/opencode/bin:\$PATH\"' >> ~/.bashrc${RESET}"
log "  ${CYAN}2.${RESET} Set up API keys at ${BOLD}~/.local/share/opencode/auth.json${RESET}"
log "     Format: ${DIM}{\"openrouter\":{\"api_key\":\"sk-or-v1-...\"}, ...}${RESET}"
log "     ${DIM}Or run 'opencode' which guides interactive auth setup.${RESET}"
log ""
log "  Get keys from:"
is_in_csv "openrouter" "$PROVIDERS" && log "     OpenRouter:  ${CYAN}https://openrouter.ai/keys${RESET}"
is_in_csv "deepseek"   "$PROVIDERS" && log "     DeepSeek:    ${CYAN}https://platform.deepseek.com/api_keys${RESET}"
is_in_csv "anthropic"  "$PROVIDERS" && log "     Anthropic:   ${CYAN}https://console.anthropic.com${RESET}"
is_in_csv "zai"        "$PROVIDERS" && log "     Z.AI:        ${CYAN}https://z.ai${RESET}"
is_in_csv "kimi"       "$PROVIDERS" && log "     Kimi:        ${CYAN}https://platform.moonshot.cn${RESET}"
log ""
log "  ${CYAN}3.${RESET} Verify:  ${BOLD}oc --doctor${RESET}"
log "  ${CYAN}4.${RESET} Open ${BOLD}~/wiki/${RESET} in Obsidian as a vault"
log "  ${CYAN}5.${RESET} Launch:  ${BOLD}oc${RESET}"
log ""
log "${DIM}Documentation: $REPO_ROOT/README.md, $REPO_ROOT/INSTALL.md${RESET}"
log ""
