#!/usr/bin/env bash
#
# occams-code installer
# Copies scripts, config, wiki template, and opencode.json to ~/.config/opencode/
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
for cmd in python3 jq curl; do
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
if [[ -f "$REPO_ROOT/bin/oc" ]]; then
  cp "$REPO_ROOT/bin/oc" "$OPENCODE_DIR/bin/oc"
  chmod +x "$OPENCODE_DIR/bin/oc"
  echo -e "  ${GREEN}✓${RESET} bin/oc"
else
  echo -e "  ${YELLOW}⚠${RESET} bin/oc not found in source"
fi

# Scripts
if ls "$REPO_ROOT"/scripts/*.py &>/dev/null; then
  cp "$REPO_ROOT"/scripts/*.py "$OPENCODE_DIR/scripts/"
  echo -e "  ${GREEN}✓${RESET} scripts/ ($(ls "$REPO_ROOT"/scripts/*.py 2>/dev/null | wc -l) files)"
else
  echo -e "  ${YELLOW}⚠${RESET} No Python scripts found in source"
fi

# Commands
if ls "$REPO_ROOT"/commands/*.md &>/dev/null; then
  cp "$REPO_ROOT"/commands/*.md "$OPENCODE_DIR/commands/"
  echo -e "  ${GREEN}✓${RESET} commands/ ($(ls "$REPO_ROOT"/commands/*.md 2>/dev/null | wc -l) files)"
else
  echo -e "  ${YELLOW}⚠${RESET} No command files found in source"
fi

# Config (don't overwrite existing — user may have customized presets/fallback)
if [[ -f "$REPO_ROOT/config/oh-my-opencode-slim.json" ]]; then
  if [[ ! -f "$OPENCODE_DIR/oh-my-opencode-slim.json" ]]; then
    cp "$REPO_ROOT/config/oh-my-opencode-slim.json" "$OPENCODE_DIR/oh-my-opencode-slim.json"
    echo -e "  ${GREEN}✓${RESET} oh-my-opencode-slim.json"
  else
    echo -e "  ${YELLOW}⊙${RESET} oh-my-opencode-slim.json (already exists, skipped)"
  fi
else
  echo -e "  ${YELLOW}⚠${RESET} config/oh-my-opencode-slim.json not found (skip)"
fi

# AGENTS.md (don't overwrite — user may have customized)
if [[ -f "$REPO_ROOT/AGENTS.md" ]]; then
  if [[ ! -f "$OPENCODE_DIR/AGENTS.md" ]]; then
    cp "$REPO_ROOT/AGENTS.md" "$OPENCODE_DIR/AGENTS.md"
    echo -e "  ${GREEN}✓${RESET} AGENTS.md"
  else
    echo -e "  ${YELLOW}⊙${RESET} AGENTS.md (already exists, skipped)"
  fi
else
  echo -e "  ${YELLOW}⚠${RESET} AGENTS.md not found in source"
fi

# --- Copy opencode.json (don't overwrite — has provider keys and personal paths) ---
echo ""
if [[ -f "$REPO_ROOT/config/opencode.json" ]]; then
  if [[ ! -f "$OPENCODE_DIR/opencode.json" ]]; then
    cp "$REPO_ROOT/config/opencode.json" "$OPENCODE_DIR/opencode.json"
    echo -e "  ${GREEN}✓${RESET} opencode.json copied"
  else
    echo -e "  ${YELLOW}⊙${RESET} opencode.json (already exists, skipped)"
  fi
else
  echo -e "${BOLD}Note:${RESET} opencode.json not in repo — run 'oc --doctor' to verify config"
fi

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
for f in wiki/wiki/concepts/karpathy-llm-wiki.md wiki/wiki/concepts/occams-code-setup.md wiki/wiki/concepts/agent-roles-and-models.md wiki/wiki/concepts/oc-launcher.md wiki/wiki/concepts/troubleshooting.md wiki/wiki/concepts/design-systems.md wiki/wiki/sources/_template-source-summary.md wiki/raw/README.md; do
  if [[ -f "$REPO_ROOT/$f" ]]; then
    # Strip leading "wiki/" from $f since $WIKI_DIR already is ~/wiki
    target="$WIKI_DIR/${f#wiki/}"
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

# Copy language conventions (with overwrite protection)
if [[ -d "$REPO_ROOT/wiki/wiki/languages" ]]; then
  for f in "$REPO_ROOT"/wiki/wiki/languages/*.md; do
    [[ -f "$f" ]] || continue
    basename="$(basename "$f")"
    target="$WIKI_DIR/wiki/languages/$basename"
    if [[ ! -f "$target" ]]; then
      cp "$f" "$target"
      echo -e "  ${GREEN}✓${RESET} wiki/wiki/languages/$basename"
    else
      echo -e "  ${YELLOW}⊙${RESET} wiki/wiki/languages/$basename (already exists, skipped)"
    fi
  done
fi

# .gitkeep files (portable: avoids {}/.gitkeep which needs GNU find)
find "$WIKI_DIR" -type d -empty -exec sh -c 'touch "$1/.gitkeep"' _ {} \; 2>/dev/null || true

# --- Install local skills ---
echo ""
echo -e "${BOLD}Installing local skills...${RESET}"
SKILLS_DIR="$HOME/.opencode/skills"
mkdir -p "$SKILLS_DIR"

# Codemap skill
if [[ -d "$REPO_ROOT/skills/codemap" ]]; then
  if [[ ! -d "$SKILLS_DIR/codemap" ]]; then
    cp -r "$REPO_ROOT/skills/codemap" "$SKILLS_DIR/codemap"
    echo -e "  ${GREEN}✓${RESET} codemap skill installed"
  else
    echo -e "  ${DIM}codemap already installed (skipped)${RESET}"
  fi
fi

# Simplify skill
if [[ -d "$REPO_ROOT/skills/simplify" ]]; then
  if [[ ! -d "$SKILLS_DIR/simplify" ]]; then
    cp -r "$REPO_ROOT/skills/simplify" "$SKILLS_DIR/simplify"
    echo -e "  ${GREEN}✓${RESET} simplify skill installed"
  else
    echo -e "  ${DIM}simplify already installed (skipped)${RESET}"
  fi
fi

# --- Install obsidian-skills plugin ---
echo ""
echo -e "${BOLD}Installing obsidian-skills plugin...${RESET}"
if [[ ! -d "$SKILLS_DIR/obsidian-skills" ]]; then
  if command -v git &>/dev/null; then
    git clone https://github.com/kepano/obsidian-skills "$SKILLS_DIR/obsidian-skills"
    echo -e "  ${GREEN}✓${RESET} obsidian-skills cloned"
  else
    echo -e "  ${YELLOW}⚠${RESET} git not found. Clone https://github.com/kepano/obsidian-skills manually to $SKILLS_DIR/obsidian-skills"
  fi
else
  echo -e "  ${DIM}obsidian-skills already installed (skipped)${RESET}"
fi

# --- Install oh-my-opencode-slim ---
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

# --- Install Obsidian ---
echo ""
echo -e "${BOLD}Obsidian (wiki viewer/editor)${RESET}"

_obsidian_installed() {
  # Check common locations across platforms
  command -v obsidian &>/dev/null && return 0
  [[ -f /Applications/Obsidian.app/Contents/MacOS/Obsidian ]] && return 0
  [[ -f "${XDG_BIN_HOME:-$HOME/.local/bin}/Obsidian.AppImage" ]] && return 0
  return 1
}

if _obsidian_installed; then
  echo -e "  ${DIM}Already installed (skipped)${RESET}"
else
  echo -e "  Obsidian provides the best wiki experience (graph view, wikilinks, backlinks)."
  echo -e "  The wiki works as plain markdown without it — Obsidian is optional but recommended."
  echo ""
  read -rp "  Install Obsidian? [Y/n] " _obsidian_answer < /dev/tty
  _obsidian_answer="${_obsidian_answer:-Y}"

  case "$_obsidian_answer" in
    [Yy]|[Yy][Ee][Ss]|'')
    _PLATFORM="$(uname -s)"
    _ARCH="$(uname -m)"

    # --- macOS ---
    if [[ "$_PLATFORM" == "Darwin" ]]; then
      if command -v brew &>/dev/null; then
        echo -e "  ${DIM}Using Homebrew (best method on macOS)...${RESET}"
        if brew install --cask obsidian 2>/dev/null; then
          echo -e "  ${GREEN}✓${RESET} Installed via Homebrew"
        else
          echo -e "  ${YELLOW}⚠${RESET} brew cask failed. Install manually: brew install --cask obsidian"
        fi
      else
        echo -e "  ${YELLOW}⚠${RESET} Homebrew not found. Install Obsidian from https://obsidian.md"
        echo -e "  ${DIM}Tip: install Homebrew first for the best experience on macOS${RESET}"
      fi

    # --- WSL ---
    elif grep -qi microsoft /proc/version 2>/dev/null; then
      echo -e "  ${DIM}WSL detected — downloading Windows installer...${RESET}"
      _OBSIDIAN_TAG=$(curl -fsSI https://github.com/obsidianmd/obsidian-releases/releases/latest 2>/dev/null \
        | grep -i '^location:' | tr -d '\r' | sed 's|.*/tag/||' || true)
      if [[ -n "$_OBSIDIAN_TAG" ]]; then
        _OBSIDIAN_VERSION="${_OBSIDIAN_TAG#v}"
        _EXE_URL="https://github.com/obsidianmd/obsidian-releases/releases/download/${_OBSIDIAN_TAG}/Obsidian-${_OBSIDIAN_VERSION}.exe"
        if command -v wslpath &>/dev/null; then
          _WIN_DL="$(wslpath "$(wslvar USERPROFILE 2>/dev/null)" 2>/dev/null)/Downloads"
          [[ -d "$_WIN_DL" ]] || _WIN_DL="$HOME"
          if curl -fSL -o "$_WIN_DL/ObsidianSetup.exe" "$_EXE_URL" 2>/dev/null; then
            echo -e "  ${GREEN}✓${RESET} Downloaded Obsidian installer to Windows Downloads folder"
            echo -e "  ${DIM}Run ObsidianSetup.exe from Windows Explorer, then open ~/wiki/ as a vault${RESET}"
          else
            echo -e "  ${YELLOW}⚠${RESET} Download failed. Get it from https://obsidian.md"
          fi
        else
          echo -e "  ${YELLOW}⚠${RESET} Download from https://obsidian.md"
        fi
      else
        echo -e "  ${YELLOW}⚠${RESET} Could not reach GitHub. Download from https://obsidian.md"
      fi

    # --- Linux ---
    elif [[ "$_PLATFORM" == "Linux" ]]; then
      _INSTALLED=false

      # Method 1: Flatpak (best for distros that support it — sandboxed, auto-updates)
      if [[ "$_INSTALLED" == "false" ]] && command -v flatpak &>/dev/null; then
        echo -e "  ${DIM}Trying Flatpak (sandboxed, auto-updating)...${RESET}"
        if flatpak install -y flathub md.obsidian.Obsidian 2>/dev/null; then
          echo -e "  ${GREEN}✓${RESET} Installed via Flatpak"
          _INSTALLED=true
        fi
      fi

      # Method 2: AppImage (works everywhere, no root needed, self-updating)
      if [[ "$_INSTALLED" == "false" ]]; then
        _OBSIDIAN_TAG=$(curl -fsSI https://github.com/obsidianmd/obsidian-releases/releases/latest 2>/dev/null \
          | grep -i '^location:' | tr -d '\r' | sed 's|.*/tag/||' || true)
        if [[ -n "$_OBSIDIAN_TAG" ]]; then
          _OBSIDIAN_VERSION="${_OBSIDIAN_TAG#v}"
          if [[ "$_ARCH" == "aarch64" || "$_ARCH" == "arm64" ]]; then
            _APPIMAGE_NAME="Obsidian-${_OBSIDIAN_VERSION}-arm64.AppImage"
          elif [[ "$_ARCH" == "x86_64" || "$_ARCH" == "amd64" ]]; then
            _APPIMAGE_NAME="Obsidian-${_OBSIDIAN_VERSION}.AppImage"
          else
            echo -e "  ${YELLOW}⚠${RESET} Unsupported architecture: $_ARCH. Download from https://obsidian.md"
            _INSTALLED=false
          fi
          if [[ -n "$_APPIMAGE_NAME" ]]; then
            _APPIMAGE_URL="https://github.com/obsidianmd/obsidian-releases/releases/download/${_OBSIDIAN_TAG}/${_APPIMAGE_NAME}"
            _INSTALL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
            mkdir -p "$_INSTALL_BIN"
            echo -e "  ${DIM}Downloading AppImage to $_INSTALL_BIN/...${RESET}"
            if curl -fSL --progress-bar -o "$_INSTALL_BIN/Obsidian.AppImage" "$_APPIMAGE_URL" 2>/dev/null; then
              chmod +x "$_INSTALL_BIN/Obsidian.AppImage"
              echo -e "  ${GREEN}✓${RESET} Installed to $_INSTALL_BIN/Obsidian.AppImage"
              # Check for libfuse2 (multiple methods for different distros)
              if ! { ldconfig -p 2>/dev/null | grep -q libfuse || find /usr/lib /usr/lib64 /usr/local/lib -name 'libfuse*' 2>/dev/null | grep -q .; }; then
                echo -e "  ${DIM}Note: AppImage requires libfuse2. Install with:${RESET}"
                echo -e "  ${DIM}  Ubuntu/Debian: sudo apt install libfuse2t64 (or libfuse2)${RESET}"
                echo -e "  ${DIM}  Fedora: sudo dnf install fuse-libs${RESET}"
                echo -e "  ${DIM}  Arch: sudo pacman -S fuse2${RESET}"
              fi
              _INSTALLED=true
            fi
          fi
        fi

        if [[ "$_INSTALLED" == "false" ]]; then
          echo -e "  ${YELLOW}⚠${RESET} Auto-install failed. Download from https://obsidian.md"
        fi
      fi
    fi
    ;;
    *)
      echo -e "  ${DIM}Skipped. Install anytime from https://obsidian.md${RESET}"
    ;;
  esac
fi
unset _obsidian_answer _PLATFORM _ARCH _INSTALLED _OBSIDIAN_TAG _OBSIDIAN_VERSION \
  _APPIMAGE_NAME _APPIMAGE_URL _INSTALL_BIN _WIN_DL _EXE_URL 2>/dev/null || true

# --- Done ---
echo ""
echo -e "${GREEN}Installation complete!${RESET}"
echo ""
echo "Next steps:"
echo "  1. Add to PATH: echo 'export PATH=\"\$HOME/.config/opencode/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
echo "  2. Set up API keys (see INSTALL.md or run 'opencode' to configure)"
echo "  3. Run: oc --doctor"
echo "  4. Open ~/wiki/ in Obsidian"
echo "  5. Launch: oc"
echo ""
