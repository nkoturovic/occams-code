# Installation Guide

This guide covers installing the occams-code OpenCode integration layer. **If you haven't installed occams-agentic yet, do that first** — it provides the universal `~/.agents/` workspace with skills, scripts, and wiki.

The installer is interactive by default and asks you exactly the right questions to set up the environment correctly. It also supports a fully **non-interactive** mode for automated/agent-driven deployments.

---

## Prerequisites

### Required (installer fails fast if missing)

| Tool | Why | How to install |
|------|-----|----------------|
| **[occams-agentic](https://github.com/nkoturovic/occams-agentic)** | Universal AI framework (`~/.agents/`) — install BEFORE occams-code | `git clone ... && cd occams-agentic && ./bin/bootstrap.sh` |
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
| OpenAI | `/connect` inside OpenCode | `openai` preset (ChatGPT Plus OAuth) |

---

## Install — Two-Step (Recommended)

### Step 1: occams-agentic (universal layer)

```bash
git clone https://github.com/nkoturovic/occams-agentic.git && cd occams-agentic
./bin/bootstrap.sh
```

This sets up `~/.agents/` — universal skills, scripts, wiki template, and AGENTS.md workspace schema.

### Step 2: occams-code (OpenCode integration layer)

```bash
cd .. && git clone https://github.com/nkoturovic/occams-code.git && cd occams-code
./scripts/install.sh
```

The installer asks:

1. **Which API providers** will you use? (OpenRouter / DeepSeek / Anthropic / Z.AI / Kimi / OpenAI — multi-select)
2. **Default preset** (`balanced` / `cheap` / `deepseek` / `premium` / `custom` / `openai`) — auto-recommended based on providers
3. **Z.AI MCPs** — only asked if you selected Z.AI; injects `zai_vision` + `web-search-prime` blocks with your API key
4. **Transcription backend** (nix whisper.cpp / system whisper-cpp / OpenAI API / skip)
5. **Optional CLIs** — `defuddle`, `agent-browser`, Obsidian
6. **Weekly cron** for log cleanup
7. **PATH setup** — appends `oc` to your shell rc
8. **API keys** — writes selected provider keys to `~/.config/secrets/env`

It confirms a summary before doing any work, then runs.

After install, set up your API keys. Occam's Code uses **two complementary secret stores**:

| Store | Path | Read by | Format |
|-------|------|---------|--------|
| **OpenCode auth** | `~/.local/share/opencode/auth.json` | OpenCode itself (per-provider) | JSON |
| **Shared env-secrets** | `~/.config/secrets/env` | Scripts (`analyze-video.py`, `transcribe`), MCPs (Exa websearch), HF model downloads | shell `export VAR=...` |

The installer's **step 8** writes the shared env-secrets file — it prompts for each selected provider's API key (input hidden), writes them to `~/.config/secrets/env` (mode 600), then ensures `~/.profile` sources the file. OpenCode's own `auth.json` can be created by running `opencode` once or by writing it manually:

**OpenCode auth.json** (per-provider keys for the agent itself):

```bash
mkdir -p ~/.local/share/opencode
cat > ~/.local/share/opencode/auth.json <<'JSON'
{
  "openrouter":      { "api_key": "sk-or-v1-..." },
  "anthropic":       { "api_key": "sk-ant-..." },
  "deepseek":        { "api_key": "..." },
  "zai-coding-plan": { "api_key": "..." },
  "kimi-for-coding": { "api_key": "..." }
}
JSON
chmod 600 ~/.local/share/opencode/auth.json
```

(Include only the providers you actually have keys for. Or run `opencode` once for the interactive auth flow.)

**Shared env-secrets** (for scripts + MCPs that read env vars):

```bash
mkdir -p ~/.config/secrets
cat > ~/.config/secrets/env <<'EOF'
export OPENROUTER_API_KEY="sk-or-v1-..."
# export DEEPSEEK_API_KEY="..."
# export ANTHROPIC_API_KEY="sk-ant-..."
# export Z_AI_API_KEY="..."
# export KIMI_API_KEY="..."
# export HF_TOKEN="hf_..."           # for transcribe model downloads, MCP integrations
# export EXA_API_KEY="..."           # for websearch MCP higher quotas
EOF
chmod 600 ~/.config/secrets/env
# Ensure ~/.profile sources it (sourced by both bash + zsh login shells):
grep -qF '.config/secrets/env' ~/.profile || \
  printf '\n[ -f "$HOME/.config/secrets/env" ] && . "$HOME/.config/secrets/env"\n' >> ~/.profile
```

A template lives at [`config/secrets-env.example`](config/secrets-env.example).

**Verify a key works** (saves debugging):

```bash
source ~/.profile
curl -sH "Authorization: Bearer $OPENROUTER_API_KEY" \
     https://openrouter.ai/api/v1/models | jq '.data | length'
# Should print a number (model count). 401 = bad key.
```

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
| `OCCAM_PROVIDERS` | csv: `openrouter,deepseek,anthropic,zai,kimi,openai` | `openrouter` |
| `OCCAM_PRESET` | `balanced` / `cheap` / `deepseek` / `premium` / `custom` / `openai` | `balanced` |
| `OCCAM_ENABLE_ZAI_MCPS` | `0` / `1` | `0` |
| `OCCAM_ZAI_API_KEY` | string | (hard-fail in unattended if `_ENABLE_ZAI_MCPS=1` and empty) |
| `OCCAM_TRANSCRIBE` | `nix` / `system` / `openai` / `skip` | `skip` |
| `OCCAM_INSTALL_DEFUDDLE` | `0` / `1` | `1` |
| `OCCAM_INSTALL_AGENT_BROWSER` | `0` / `1` | `1` |
| `OCCAM_INSTALL_OBSIDIAN` | `0` / `1` | `1` |
| `OCCAM_SETUP_CRON` | `0` / `1` | `1` |
| `OCCAM_SETUP_PATH` | `0` / `1` | `1` |
| `OCCAM_SETUP_SECRETS` | `0` / `1` — write `~/.config/secrets/env` | `1` |
| `OCCAM_OPENROUTER_KEY` | string | (interactive prompt unless set) |
| `OCCAM_DEEPSEEK_KEY` | string | (interactive) |
| `OCCAM_ANTHROPIC_KEY` | string | (interactive) |
| `OCCAM_KIMI_KEY` | string | (interactive) |
| `OCCAM_HF_TOKEN` | string | (interactive, optional) |
| `OCCAM_EXA_API_KEY` | string | (interactive, optional) |
| `OCCAM_OPENCODE_DIR` | path | `$HOME/.config/opencode` |
| `OCCAM_WIKI_DIR` | path | `$HOME/.agents/wiki` |

**CLI flags** (override env vars): `--preset NAME`, `--providers CSV`, `--transcribe MODE`, `--no-defuddle`, `--no-agent-browser`, `--no-obsidian`, `--no-cron`, `--no-path`, `--enable-zai`, `--zai-key KEY`, `--dry-run` (preview without writing), `--unattended`.

The installer is idempotent: re-running skips files that already exist (no destructive overwrites of your customizations). `bin/oc`, `scripts/*`, and `commands/*` are always overwritten so upstream fixes propagate; user-editable files (`AGENTS.md`, `opencode.json`, `oh-my-opencode-slim.json`, `model-profile.jsonc`) are preserved if they exist.

---

## Manual Install (Advanced / Troubleshooting)

If you'd rather control every step, follow the two-repo manual install:

### Step 1: occams-agentic (universal layer)

```bash
git clone https://github.com/nkoturovic/occams-agentic.git
cd occams-agentic
./bin/bootstrap.sh   # creates ~/.agents/ with skills, scripts, wiki template, and AGENTS.md
```

### Step 2: occams-code (OpenCode layer)

```bash
git clone https://github.com/nkoturovic/occams-code.git
cd occams-code

# Create directories
mkdir -p ~/.config/opencode/{bin,scripts,commands,skills}

# Core files
cp bin/oc                            ~/.config/opencode/bin/oc          && chmod +x ~/.config/opencode/bin/oc
cp scripts/*.py                      ~/.config/opencode/scripts/
cp scripts/cleanup-logs.sh           ~/.config/opencode/scripts/        && chmod +x ~/.config/opencode/scripts/cleanup-logs.sh
cp commands/*.md                     ~/.config/opencode/commands/
cp AGENTS.md                         ~/.config/opencode/AGENTS.md
cp config/model-profile.jsonc        ~/.config/opencode/model-profile.jsonc
cp config/opencode.json              ~/.config/opencode/opencode.json
cp config/oh-my-opencode-slim.json   ~/.config/opencode/oh-my-opencode-slim.json

# OpenCode-specific skills
cp -r skills/codemap         ~/.config/opencode/skills/
cp -r skills/simplify        ~/.config/opencode/skills/
cp -r skills/clonedeps       ~/.config/opencode/skills/

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

## Z.AI MCPs

The default config ships `zai_vision` and `web-search-prime` MCPs as enabled. They require `Z_AI_API_KEY` to be set in your environment (the config uses `{env:Z_AI_API_KEY}` template). Without the key, they fail silently — the agent falls back to the built-in multimodal observer and Exa websearch.

To activate, set the key:

```bash
# Add to ~/.config/secrets/env
export Z_AI_API_KEY="your-zai-api-key"
source ~/.profile
```

The installer also offers to set this up during interactive install (Q3).

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

# Then edit ~/.agents/scripts/transcribe and replace the last line:
#   exec nix run "${FLAKE}#whisper-cpp-vulkan" -- "${WHISPER_ARGS[@]}" "$@"
# with:
#   exec whisper-cli "${WHISPER_ARGS[@]}" "$@"
```

### OpenAI Whisper API (any platform, ~$0.006/min)

Replace the body of `~/.agents/scripts/transcribe` with a `curl` call to `https://api.openai.com/v1/audio/transcriptions`. Reference: https://platform.openai.com/docs/api-reference/audio

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
- Wiki structure: `~/.agents/wiki/AGENTS.md`, `index.md`, `raw/`, topic dirs all present
- Wiki index has ≥ 3 entries
- Runs `wiki-lint.py` to check dead links / orphans / stale pages

---

## Updating

```bash
cd /path/to/occams-code
git pull
./scripts/install.sh --unattended    # idempotent — preserves your customizations
```

**What gets overwritten on update:**
- `bin/oc` — always (script bug fixes should propagate)
- `scripts/*` — always (the OpenCode-specific Python utilities)
- `commands/*` — always (slash command docs)

**What is preserved if it exists:**
- `AGENTS.md` (you may have customized session rules)
- `opencode.json` (provider config, MCP entries — including any Z.AI blocks you injected)
- `oh-my-opencode-slim.json` (your preset / agent / fallback overrides)
- `model-profile.jsonc` (your model assignments)
- `~/.config/secrets/env` (your API keys — never overwritten)
- Wiki content under `~/.agents/wiki/` (your knowledge base)

To force-update a preserved file, delete it first:

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
# rm -rf ~/.agents/wiki/

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
| `oc --doctor` says wiki structure incomplete | Wiki dirs missing | Re-run occams-agentic `./bin/bootstrap.sh` |
| `transcribe` fails with "nix not found" | Selected nix backend without nix installed | Install nix, OR re-run installer and pick `system`/`openai`/`skip` |
| `defuddle` not in PATH after install | npm prefix not in PATH | Installer auto-symlinks to `~/.local/bin/`; ensure that's in your PATH |
| Z.AI MCPs show as "disabled" in `oc` | You opted in but the API key is wrong | Edit `~/.config/opencode/opencode.json` `Z_AI_API_KEY` |
| `analyze-video.py: OPENROUTER_API_KEY not set` | Shell hasn't sourced `~/.config/secrets/env` | `source ~/.profile` in current shell, or open a new terminal |
| `transcribe` fails to download model | HuggingFace rate limit | Set `HF_TOKEN` in `~/.config/secrets/env`, then `source ~/.profile` |
| websearch MCP returns "rate limited" | Free Exa tier exhausted | Set `EXA_API_KEY` in `~/.config/secrets/env` |

For more, see `~/.agents/wiki/concepts/troubleshooting.md` if your wiki includes the troubleshooting page.
