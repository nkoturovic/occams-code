---
name: upkeep
description: Keep the live OpenCode setup and the occams-code / occams-agentic repos up to date and in sync. Use when the user says "upkeep", "update everything", "sync repos", "upgrade oh-my-opencode-slim", "upgrade OpenCode", or asks to keep the setup current. NOT for ordinary project work, model swaps, or one-off config edits.
---

# Upkeep Skill

End-to-end maintenance of the local OpenCode/Occams stack and the two public
repos. Treat this as a **gated workflow**: research → plan → review → execute →
verify → sync → commit. Do not skip gates.

## Scope

| Layer | Path | Repo |
|-------|------|------|
| Live OpenCode config | `~/.config/opencode` | local-only (no remote) |
| Public OpenCode layer | `~/personal/repos/occams-code` | GitHub: `<your-user>/occams-code` |
| Universal framework live | `~/.agents` | local working copy |
| Public universal framework | `~/personal/repos/occams-agentic` | GitHub: `<your-user>/occams-agentic` |

`occams-code → occams-agentic`: OpenCode layer depends on universal framework.
Universal pieces go to occams-agentic; OpenCode-specific pieces go to occams-code.

## Hard Rules

- **No push without explicit user approval.** Commit is OK when requested; push needs a separate yes.
- **No package installs without explicit approval.** `npm i`, `bun add`, `pip`, `apt`, OpenCode self-upgrade, etc. — propose first, wait for yes.
- **Explicit path staging only.** Never `git add .` or `git add -A`.
- **Never commit secrets.** `auth.json`, `budget.json`, `mcp-oauth.json`, `.env*`, `secrets/`, real API keys, real tokens.
- **Restart required.** Config/plugin/launcher changes apply on next OpenCode run. Tell the user.

## Phase 1 — Baseline & Discovery

Record current state before changing anything.

1. **Live git status**: `git -C ~/.config/opencode status --short`
2. **Live versions**:
   ```bash
   opencode --version
   plugin_spec="$(jq -r '.plugin[] | select(startswith("oh-my-opencode-slim@"))' ~/.config/opencode/opencode.json)"
   node -p "require(process.env.HOME + '/.cache/opencode/packages/${plugin_spec}/node_modules/oh-my-opencode-slim/package.json').version"
   opencode debug config | grep plugin_origins
   ```
   Read the exact configured spec first. The cache directory must match that
   exact pin; never substitute an `@latest` cache path.
3. **npm latest**: `npm view oh-my-opencode-slim version` (network; read-only query, OK without approval)
4. **Repo states**: `git -C ~/personal/repos/occams-code status --short` and `git -C ~/personal/repos/occams-agentic status --short`
5. **Classify pre-existing dirty changes** in live before staging upgrade edits.

If the live repo is already dirty, record what and why. Do not bundle unrelated changes into an upkeep commit.

## Phase 2 — Plan & Review

Decide what actually needs updating. Not every run touches everything.

- **Plugin upgrade**: only if pinned spec in `opencode.json`/`tui.json` is older than npm latest, and the changelog has relevant fixes.
- **OpenCode core upgrade**: only if current version has a known bug or the user explicitly asks. Propose, do not run.
- **Docs/skills drift**: run stale-string greps (see Phase 5 checks). Fix only what is actually stale.
- **Config drift**: `scripts/doctor-model-check.py`, `scripts/model-profile.py` regeneration diff.

Use DeepWork (`/deepwork`) for risky/multi-phase upkeep. For small upkeep, this skill alone is enough.

Oracle review is required for:
- plugin version bumps,
- OpenCode core upgrade proposals,
- anything that changes provider timeouts or output caps.

## Phase 3 — Execute (live)

Apply changes to live `~/.config/opencode` first.

- Pin the plugin spec to the exact selected version in both `opencode.json` and
  `tui.json` (format: `"oh-my-opencode-slim@<exact-version>"`). Bare
  `"oh-my-opencode-slim"` is cache-ambiguous.
- Regenerate `oh-my-opencode-slim.json` from `model-profile.jsonc` only if the source changed:
  `python3 scripts/model-profile.py model-profile.jsonc oh-my-opencode-slim.json`
- Keep provider timeouts and output caps as deliberate mitigations; do not silently revert.
- Launcher edits (`bin/oc`): keep multiplexer detection covering all supported backends (tmux/zellij/herdr).

## Phase 4 — Verify (live)

Run all of these. If any fail, stop and fix before syncing.

```bash
python3 scripts/model-profile.py model-profile.jsonc /tmp/upkeep-gen.json
diff -u oh-my-opencode-slim.json /tmp/upkeep-gen.json        # must be empty
OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX=131072 python3 scripts/doctor-model-check.py
jq empty opencode.json oh-my-opencode-slim.json tui.json
bash -n bin/oc
bin/oc --doctor
opencode debug config > /tmp/upkeep-debug.json               # confirm plugin_origins spec
```

Optional deeper checks:

- Synthetic project override merge test (proves omo-slim `presets` deep-merge semantics).
- `/loop` command registration visible in `opencode debug config`.
- Stale-string grep across live docs (Phase 5).

## Phase 5 — Sync to Repos

Mirror only intended, scrubbed files. See `~/.agents/wiki/patterns/sync-live-repo.md` for the full map.

occams-code (OpenCode-specific): `bin/oc`, `scripts/*.py`, `commands/`, `skills/`, `config/{model-profile.jsonc,oh-my-opencode-slim.json,opencode.json,tui.json}`, `AGENTS.md`, `.gitignore`.

occams-agentic (universal): `~/.agents/AGENTS.md`, `conventions/`, `scripts/`, `skills/` (universal only).

Scrub checklist before copying to repos:
- [ ] Default preset in occams-code `config/` is `balanced` (not live `custom`).
- [ ] Regenerate `config/oh-my-opencode-slim.json` in occams-code from the repo's own `config/model-profile.jsonc`.
- [ ] No `/home/<user>/` paths, no real keys/tokens, no personal project names.
- [ ] `{env:VAR}` placeholders stay; real `Authorization: Bearer ...` must not.
- [ ] MCP/baseURL entries are generic or env-templated.

Copy with explicit `cp`/`cp -a` paths. Then `git -C <repo> status --short` to confirm only intended files changed.

## Phase 6 — Secret Scan & Commit

Before any commit:

```bash
# Secret scan across all three repos (should print nothing)
rg -n "sk-[A-Za-z0-9]{20,}|Bearer [A-Za-z0-9]{20,}|Authorization:.{0,20}[A-Za-z0-9]{20,}" \
  ~/personal/repos/occams-code ~/personal/repos/occams-agentic ~/.config/opencode || true

# Personal-path scan in public repos
rg -n "/home/[a-z_]+/" ~/personal/repos/occams-code ~/personal/repos/occams-agentic || true
```

Commit with concise messages. Stage explicit paths only.

- Live repo: local-only, commit freely when asked.
- occams-code / occams-agentic: commit when asked, **do not push** without a separate yes.

Suggested message style (match existing repo history):

```
upgrade: oh-my-opencode-slim 2.0.5 → 2.1.0 (herdr, /loop, project deep-merge)
fix: narrow anti-loop guard to identical failed retries
docs: refresh project-local customization for v2.1.0
```

## Phase 7 — Log

Append a brief entry to `~/.agents/wiki/log.md`:

```
## [YYYY-MM-DD] upgrade|fix|docs | <short title>
Project: opencode (~/.config/opencode)
Pages updated: log.md[, others]
Scripts/config updated: <files>
Changes:
- <bullet points>
- Commits: live <sha>, occams-code <sha>[, occams-agentic <sha>]
```

## When NOT to Use This Skill

- Single model swap → use `/model-switch`.
- One-off config edit → edit directly, run `doctor-model-check.py`.
- Adding a custom agent → use `oh-my-opencode-slim` skill.
- Heavy multi-phase refactor → use `/deepwork`.

## Related

- `~/.agents/wiki/patterns/sync-live-repo.md` — full sync runbook and scrubbing checklist
- `~/.agents/wiki/concepts/model-profile-guide.md` — model swap and per-project override rules
- `oh-my-opencode-slim` skill — plugin/prompt/agent tuning
- `deepwork` skill — gated workflow for risky changes
