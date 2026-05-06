# Installation Guide

This guide covers installing Occam's Code on a fresh machine.

The installer is interactive by default and asks you exactly the right questions to set up the environment correctly. It also supports a fully **non-interactive** mode for automated/agent-driven deployments.

---

## Supported Platforms

| Platform | Status | Notes |
|----------|--------|-------|
| Linux x86_64 | ✅ Full | Default bash 5+ on most distros |
| Linux aarch64 | ✅ Full | Tested on Raspberry Pi 5, Asahi |
| macOS Apple Silicon | ✅ Full | Requires `brew install bash` (system bash 3.2 fails) |
| macOS Intel | ✅ Full | Requires `brew install bash` |
| Windows (WSL2) | ✅ Full | Same as Linux inside WSL |
| Windows native | ❌ | Use WSL2 |

---

## Prerequisites

### Required (installer fails fast if missing)

| Tool | Why | How to install |
|------|-----|----------------|
| `python3` ≥ 3.10 | Wiki + project scripts | `apt install python3` / `brew install python3` |
| `jq` | JSON parsing in `oc` | `apt install jq` / `brew install jq` |
| `curl` | Downloads, MCP requests | usually preinstalled |
| `git` | Plugin install, repo ingest, wiki versioning | `apt install git` / `brew install git` |
| `bash` ≥ 4.0 | `oc` launcher uses bash 4 features | macOS: `brew install bash` (system bash is 3.2) |

### Optional but recommended

| Tool | Purpose |
|------|---------|
| `npm` or `bun` | Installs `oh-my-opencode-slim` plugin and optional CLIs |
| `nix` | Cleanest path for whisper.cpp transcription (Linux/WSL) |
| `fzf` | Nicer interactive picker (not required) |
| `crontab` | Weekly log cleanup |

### API keys

You need **at least one** provider. The default `balanced` preset works with just an OpenRouter key.

| Provider | Get key | Use case |
|----------|---------|----------|
| OpenRouter | https://openrouter.ai/keys | **Recommended default** — 400+ models, single key, pay-per-token |
| DeepSeek | https://platform.deepseek.com/api_keys | Direct V4 Pro / V4 Flash (best DeepSeek experience) |
| Anthropic | https://console.anthropic.com | `premium` preset (Claude Opus 4.7) |
| Z.AI | https://z.ai | `custom` preset + Z.AI MCPs (subscription) |
| Kimi for Coding | https://platform.moonshot.cn | `custom` preset (subscription) |

---

## Install — Interactive (Recommended)

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code
./scripts/install.sh
```

The installer asks:

1. **Which API providers** will you use? (OpenRouter / DeepSeek / Anthropic / Z.AI / Kimi — multi-select)
2. **Default preset** (`balanced` / `cheap` / `premium` / `custom`) — auto-recommended based on providers
3. **Z.AI MCPs** — only asked if you selected Z.AI; injects `zai_vision` + `web-search-prime` blocks with your API key
4. **Transcription backend** (nix whisper.cpp / system whisper-cpp / OpenAI API / skip)
5. **Optional CLIs** — `defuddle`, `agent-browser`, Obsidian
6. **Weekly cron** for log cleanup
7. **PATH setup** — appends `oc` to your shell rc

It confirms a summary before doing any work, then runs.

After install, set up your API keys:

```bash
mkdir -p ~/.local/share/opencode
cat > ~/.local/share/opencode/auth.json <<'JSON'
{
  "openrouter": { "api_key": "sk-or-v1-..." }
}
JSON
chmod 600 ~/.local/share/opencode/auth.json
```

Or just run `opencode` once and it'll guide you through it.

Verify everything is healthy:

```bash
oc --doctor
```

Launch:

```bash
oc
```

---

## Install — Unattended (For AI Agents / CI)

Set environment variables, then run with `--unattended`:

```bash
OCCAM_PROVIDERS=openrouter \
OCCAM_PRESET=balanced \
OCCAM_TRANSCRIBE=skip \
OCCAM_INSTALL_DEFUDDLE=1 \
OCCAM_INSTALL_AGENT_BROWSER=1 \
OCCAM_INSTALL_OBSIDIAN=0 \
OCCAM_SETUP_CRON=1 \
OCCAM_SETUP_PATH=1 \
./scripts/install.sh --unattended
```

### All variables

| Variable | Values | Default |
|----------|--------|---------|
| `OCCAM_PROVIDERS` | csv: `openrouter,deepseek,anthropic,zai,kimi` | `openrouter` |
| `OCCAM_PRESET` | `balanced` / `cheap` / `premium` / `custom` | `balanced` |
| `OCCAM_ENABLE_ZAI_MCPS` | `0` / `1` | `0` |
| `OCCAM_ZAI_API_KEY` | string | (empty placeholder) |
| `OCCAM_TRANSCRIBE` | `nix` / `system` / `openai` / `skip` | `skip` |
| `OCCAM_INSTALL_DEFUDDLE` | `0` / `1` | `1` |
| `OCCAM_INSTALL_AGENT_BROWSER` | `0` / `1` | `1` |
| `OCCAM_INSTALL_OBSIDIAN` | `0` / `1` | `1` |
| `OCCAM_SETUP_CRON` | `0` / `1` | `1` |
| `OCCAM_SETUP_PATH` | `0` / `1` | `1` |
| `OCCAM_OPENCODE_DIR` | path | `$HOME/.config/opencode` |
| `OCCAM_WIKI_DIR` | path | `$HOME/wiki` |

The installer is idempotent: re-running skips files that already exist (no destructive overwrites of your customizations).

---

## Manual Install (Advanced / Troubleshooting)

If you'd rather control every step:

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code

# Create directories
mkdir -p ~/.config/opencode/{bin,scripts,commands,skills}
mkdir -p ~/wiki/raw/{articles,papers,repos,docs,forums,assets,_inbox}
mkdir -p ~/wiki/wiki/{projects,domain,languages,patterns,concepts,entities,sources,comparisons}

# Core files
cp bin/oc                            ~/.config/opencode/bin/oc          && chmod +x ~/.config/opencode/bin/oc
cp scripts/*.py                      ~/.config/opencode/scripts/
cp scripts/transcribe                ~/.config/opencode/scripts/        && chmod +x ~/.config/opencode/scripts/transcribe
cp scripts/cleanup-logs.sh           ~/.config/opencode/scripts/        && chmod +x ~/.config/opencode/scripts/cleanup-logs.sh
cp commands/*.md                     ~/.config/opencode/commands/
cp AGENTS.md                         ~/.config/opencode/AGENTS.md
cp model-profile.jsonc               ~/.config/opencode/model-profile.jsonc
cp config/opencode.json              ~/.config/opencode/opencode.json
cp config/oh-my-opencode-slim.json   ~/.config/opencode/oh-my-opencode-slim.json

# Wiki template
cp wiki/AGENTS.md  wiki/index.md  wiki/log.md  wiki/overview.md  wiki/.gitignore  ~/wiki/
cp -r wiki/.obsidian                                              ~/wiki/
cp wiki/wiki/concepts/*.md                                        ~/wiki/wiki/concepts/
cp wiki/raw/README.md                                             ~/wiki/raw/README.md
cp wiki/wiki/sources/_template-source-summary.md                  ~/wiki/wiki/sources/ 2>/dev/null || true
find ~/wiki -type d -empty -exec touch {}/.gitkeep \;

# Local skills
cp -r skills/codemap         ~/.config/opencode/skills/
cp -r skills/simplify        ~/.config/opencode/skills/
cp -r skills/audio-analysis  ~/.config/opencode/skills/
cp -r skills/video-analysis  ~/.config/opencode/skills/
cp -r skills/lecture-notes   ~/.config/opencode/skills/

# Plugin
cd ~/.config/opencode && npm install oh-my-opencode-slim   # or 'bun install ...'

# Obsidian-skills bundle (optional)
mkdir -p ~/.opencode/skills
git clone --depth=1 https://github.com/kepano/obsidian-skills ~/.opencode/skills/obsidian-skills

# PATH
echo 'export PATH="$HOME/.config/opencode/bin:$PATH"' >> ~/.bashrc   # or ~/.zshrc
source ~/.bashrc
```

Set the default preset:

```bash
jq '.preset = "balanced"' ~/.config/opencode/oh-my-opencode-slim.json > /tmp/c.json \
    && mv /tmp/c.json ~/.config/opencode/oh-my-opencode-slim.json
```

---

## Z.AI MCPs (Opt-in)

The default repo config does **not** include `zai_vision` or `web-search-prime` MCPs — they're redundant with the multimodal observer agent + Exa websearch (built-in plugin) for users without Z.AI subscription.

To enable them after install (or if you skipped them during install):

```bash
ZAI_KEY="your-zai-api-key"

jq --arg key "$ZAI_KEY" '
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
' ~/.config/opencode/opencode.json > /tmp/c.json \
  && mv /tmp/c.json ~/.config/opencode/opencode.json
```

The agent-config `mcps` lists in `oh-my-opencode-slim.json` already reference these names — no further changes needed.

---

## Transcription backends

The `transcribe` script ships expecting nix-built whisper.cpp from `kotur-nixpkgs`. Other paths:

### Linux/WSL with nix (default if you select option 1)

Already works after install. The flake `github:nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan` is fetched on first run; the model is auto-downloaded to `~/.local/share/opencode/models/whisper/`.

### macOS or Linux without nix — system whisper-cpp

```bash
# macOS
brew install whisper-cpp

# Then edit ~/.config/opencode/scripts/transcribe and replace the last line:
#   exec nix run "${FLAKE}#whisper-cpp-vulkan" -- "${WHISPER_ARGS[@]}" "$@"
# with:
#   exec whisper-cli "${WHISPER_ARGS[@]}" "$@"
```

### OpenAI Whisper API (any platform, ~$0.006/min)

Replace the body of `scripts/transcribe` with a `curl` call to `https://api.openai.com/v1/audio/transcriptions`. Reference: https://platform.openai.com/docs/api-reference/audio

### Skip

If you don't need lecture notes / audio transcription, just leave `OCCAM_TRANSCRIBE=skip`. The `transcribe` script remains in place but won't work without one of the above.

---

## macOS Bash 5

macOS ships bash 3.2, but `bin/oc` requires bash 4+:

```bash
brew install bash

# Option A: run oc explicitly with brew bash (no PATH changes)
/opt/homebrew/bin/bash ~/.config/opencode/bin/oc      # Apple Silicon
/usr/local/bin/bash    ~/.config/opencode/bin/oc      # Intel

# Option B: change login shell (transparent)
echo '/opt/homebrew/bin/bash' | sudo tee -a /etc/shells
chsh -s /opt/homebrew/bin/bash
# then restart terminal — `bash --version` should show 5.x
```

---

## Verification

After install, run:

```bash
oc --doctor
```

Checks:
- `opencode.json` and `oh-my-opencode-slim.json` are valid JSON
- Project config (if `.opencode/oh-my-opencode-slim.jsonc` exists) is valid
- Wiki structure: `~/wiki/AGENTS.md`, `index.md`, `raw/`, `wiki/` all present
- Wiki index has ≥ 3 entries
- Runs `wiki-lint.py` to check dead links / orphans / stale pages

---

## Updating

```bash
cd /path/to/occams-code
git pull
./scripts/install.sh --unattended    # idempotent — preserves your customizations
```

The installer skips files that already exist (your custom `oh-my-opencode-slim.json`, `opencode.json`, `AGENTS.md` are safe). Scripts and `bin/oc` are always updated to track upstream fixes.

To force-update one of the protected files, delete it first:

```bash
rm ~/.config/opencode/AGENTS.md
./scripts/install.sh --unattended
```

---

## Uninstall

```bash
# Files (preserves auth.json, your wiki content, customizations)
rm -rf ~/.config/opencode/{bin,scripts,commands,skills}
rm -f  ~/.config/opencode/{AGENTS.md,model-profile.jsonc,oh-my-opencode-slim.json}
rm -f  ~/.config/opencode/opencode.json   # CAREFUL — has your provider/MCP config

# Plugin
rm -rf ~/.config/opencode/node_modules ~/.config/opencode/package.json

# Optional: remove obsidian-skills bundle
rm -rf ~/.opencode/skills/obsidian-skills

# PATH (manually edit ~/.bashrc / ~/.zshrc to remove the export line)

# Cron (only if you set it up)
crontab -l | grep -v cleanup-logs.sh | crontab -

# Wiki (BACK UP FIRST — your knowledge base lives here!)
# rm -rf ~/wiki/

# auth.json (your API keys — usually keep)
# rm ~/.local/share/opencode/auth.json
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `bash: bin/oc: bash 4 required` | macOS bash 3.2 | `brew install bash`; see [macOS Bash 5](#macos-bash-5) |
| `Config not found: oh-my-opencode-slim.json` | Plugin install failed | `cd ~/.config/opencode && npm install oh-my-opencode-slim` |
| `jq: command not found` | jq missing | `apt install jq` / `brew install jq` |
| Models not loading | Auth.json missing or invalid | `cat ~/.local/share/opencode/auth.json \| jq .` should succeed |
| `oc --doctor` says wiki structure incomplete | Wiki dirs missing | Re-run `./scripts/install.sh --unattended` |
| `transcribe` fails with "nix not found" | Selected nix backend without nix installed | Install nix, OR re-run installer and pick `system`/`openai`/`skip` |
| `defuddle` not in PATH after install | npm prefix not in PATH | Installer auto-symlinks to `~/.local/bin/`; ensure that's in your PATH |
| Z.AI MCPs show as "disabled" in `oc` | You opted in but the API key is wrong | Edit `~/.config/opencode/opencode.json` `Z_AI_API_KEY` |

For more, see [`wiki/wiki/concepts/troubleshooting.md`](wiki/wiki/concepts/troubleshooting.md).
