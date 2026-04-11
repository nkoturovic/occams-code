# Installation Guide

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux (x86_64) | ✅ Full | Default bash is fine |
| macOS (Apple Silicon) | ✅ Full | Requires bash 5 via Homebrew |
| macOS (Intel) | ✅ Full | Requires bash 5 via Homebrew |
| Windows (WSL) | ✅ Full | WSL2 recommended |
| Windows (native) | ❌ Not supported | Use WSL |

## Prerequisites

### Required

| Dependency | Install | Check |
|-----------|---------|-------|
| OpenCode | `npm install -g opencode` or `bun install -g opencode` | `opencode --version` |
| Python 3.10+ | System package manager | `python3 --version` |
| Bash 4.0+ | System default (Linux) or `brew install bash` (macOS) | `bash --version` |
| jq | `sudo apt install jq` / `brew install jq` | `jq --version` |
| fzf | `sudo apt install fzf` / `brew install fzf` | `fzf --version` |

### Optional

| Dependency | Purpose | Install |
|-----------|---------|---------|
| [Obsidian](https://obsidian.md) | Wiki viewer/editor | Download from obsidian.md |
| [uv](https://github.com/astral-sh/uv) | Python package management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| git | Repo ingestion, wiki versioning | System package manager |

### API Keys

You need at least one provider API key:

| Provider | Get Key | Cost |
|----------|---------|------|
| [OpenRouter](https://openrouter.ai) | openrouter.ai/keys | Pay-per-token, 400+ models |
| [Anthropic](https://console.anthropic.com) | console.anthropic.com | Direct Claude API |
| [Z.AI](https://z.ai) | z.ai | Subscription (GLM-5.1) |

Store keys in `~/.local/share/opencode/auth.json` (OpenCode handles this on first run).

## Installation

### Option A: Automated (Recommended)

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code
chmod +x scripts/install.sh
./scripts/install.sh
```

### Option B: Manual

```bash
# 1. Clone
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code

# 2. Copy scripts and commands
cp -r bin/ ~/.config/opencode/bin/
cp -r scripts/ ~/.config/opencode/scripts/
cp -r commands/ ~/.config/opencode/commands/
chmod +x ~/.config/opencode/bin/oc

# 3. Copy preset config
cp config/oh-my-opencode-slim.json ~/.config/opencode/oh-my-opencode-slim.json

# 4. Copy AGENTS.md
cp AGENTS.md ~/.config/opencode/AGENTS.md

# 5. Generate opencode.json with your home directory
python3 scripts/generate-config.py

# 6. Copy wiki template
cp -r wiki/ ~/wiki/

# 7. Install oh-my-opencode-slim plugin
cd ~/.config/opencode/
npm install oh-my-opencode-slim   # or: bun install oh-my-opencode-slim
```

### macOS: Bash 5 Setup

macOS ships bash 3.2 which is incompatible with Occam's Code. Install bash 5:

```bash
brew install bash
```

**Important:** The scripts use `#!/usr/bin/env bash` which resolves via PATH. After installing bash 5, you have two options:

**Option 1: Run installer explicitly with bash 5 (recommended)**
```bash
# Apple Silicon
/opt/homebrew/bin/bash scripts/install.sh

# Intel Macs
/usr/local/bin/bash scripts/install.sh
```

**Option 2: Change login shell (makes all scripts work automatically)**
```bash
# Add brew bash to /etc/shells
echo '/opt/homebrew/bin/bash' | sudo tee -a /etc/shells   # Apple Silicon
# echo '/usr/local/bin/bash' | sudo tee -a /etc/shells    # Intel Macs

# Set as default shell
chsh -s /opt/homebrew/bin/bash

# Restart terminal, then verify:
env bash --version   # Should show 5.x
```

### macOS: fzf Setup

`brew install fzf` installs the binary but does not set up shell keybindings. To enable them:

```bash
$(brew --prefix)/opt/fzf/install
# Then restart your shell
```

## Post-Install Setup

### Add `oc` to PATH

```bash
echo 'export PATH="$HOME/.config/opencode/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify:
oc --help
```

### API Keys

You need at least one provider API key. Create `~/.local/share/opencode/auth.json`:

```json
{
  "openrouter": {
    "api_key": "sk-or-v1-..."
  },
  "anthropic": {
    "api_key": "sk-ant-..."
  }
}
```

Only include providers you have keys for. OpenRouter is recommended as the primary provider (400+ models, pay-per-token).

Get keys from:
- [OpenRouter](https://openrouter.ai/keys) — recommended, works out of the box
- [Anthropic](https://console.anthropic.com) — for Claude models
- [Z.AI](https://z.ai) — subscription plan (GLM-5.1)

### Verify Installation

```bash
oc --doctor
```

This checks:
- Model config validation
- AGENTS.md sync with config
- Wiki structure
- Obsidian vault
- Project wiki page
- Wiki freshness
- Provider health

## Uninstall

```bash
# Remove Occam's Code files (preserves auth.json and any personal data)
rm -rf ~/.config/opencode/bin/oc
rm -rf ~/.config/opencode/scripts/
rm -rf ~/.config/opencode/commands/
rm ~/.config/opencode/AGENTS.md
rm ~/.config/opencode/oh-my-opencode-slim.json

# Optionally remove wiki (YOUR KNOWLEDGE BASE — back up first!)
# rm -rf ~/wiki/

# Optionally remove generated config
# rm ~/.config/opencode/opencode.json
```

## Troubleshooting

### "bash version too old" error (macOS)
Install bash 5 via Homebrew (see macOS section above).

### "Config not found" error
Ensure `~/.config/opencode/oh-my-opencode-slim.json` exists.

### Models not loading
Run `opencode models --refresh` and verify API keys in auth.json.
