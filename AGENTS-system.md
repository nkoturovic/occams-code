# AI Agent System — ~/.agents/

This directory is the unified agent home. It contains everything an AI agent needs:
persistent knowledge, source material, capabilities, and workspace.

## Directory Layout

```
~/.agents/
├── AGENTS.md              ← This file (tool-agnostic system schema)
├── wiki/                  ← LLM Wiki (Obsidian vault, git repo)
│   ├── AGENTS.md          ← Wiki schema (Karpathy Layer 3 — how to maintain the wiki)
│   ├── index.md           ← Master catalog (session-start entry point)
│   ├── log.md             ← Append-only activity log
│   ├── overview.md        ← High-level synthesis
│   ├── raw/               ← Immutable source documents (read-only)
│   │   ├── repos/ → ../../repos/   ← symlink to cloned repos outside vault
│   │   └── ...            ← articles/, papers/, docs/, assets/, etc.
│   ├── concepts/          ← Topic: architectural concepts
│   ├── entities/          ← Topic: people, orgs, tools
│   ├── projects/          ← Topic: per-project knowledge
│   ├── domain/            ← Topic: cross-project facts
│   ├── languages/         ← Topic: coding conventions
│   ├── patterns/          ← Topic: proven reusable patterns
│   ├── sources/           ← Topic: source summaries
│   └── comparisons/       ← Topic: comparisons
├── repos/                 ← Cloned git repos (outside vault)
├── scratch/               ← Ephemeral agent workspace (no persistence)
└── skills/                ← Tool-agnostic ecosystem skills
```

## Three-Layer Architecture (Karpathy LLM-Wiki)

1. **raw/** — Immutable source documents. Agent reads, never writes.
2. **wiki/** — LLM-generated compiled knowledge. Agent owns this layer.
3. **AGENTS.md** — Schema telling the agent how to maintain the wiki.

## Session Start Protocol

1. Read `wiki/index.md` to discover available knowledge
2. Check `wiki/log.md` for recent activity
3. Apply relevant context from wiki pages before starting any task
4. When maintaining wiki, read `wiki/AGENTS.md` for conventions

## Skill Shadowing

Skills are discovered from multiple directories. When the same skill name exists
in both `~/.agents/skills/` (tool-agnostic) and a tool-specific directory
(e.g., `~/.config/opencode/skills/`), the tool-specific version wins.

Tool-agnostic skills provide base instructions. Tool-specific skills can override
with tool-specific additions.

## Project-Level Symmetry

Each project can have a `.agents/` directory following the same pattern:

```
project/AGENTS.md              ← Project agent instructions (at project root)
project/.agents/wiki/           ← Project knowledge
project/.agents/wiki/AGENTS.md   ← Project-local wiki schema
project/.agents/wiki/raw/       ← Project sources (repos/ symlink points out)
project/.agents/repos/          ← Project cloned repos / external source clones
project/.agents/scratch/        ← Project ephemeral
project/.agents/skills/         ← Project skills
```

Project `.agents/` mirrors global `~/.agents/` except for `AGENTS.md`: project
instructions stay at the project root (sibling to `.agents/`) so OpenCode and
the agents.md standard can discover them while walking up from the cwd. Do not
put the primary project instructions at `project/.agents/AGENTS.md`; tools will
not reliably load them there.

The directory structure above is a recommendation, not a rigid requirement.
Projects vary — some may not need `raw/` or `scratch/`, others may add
topic-specific subdirectories under `wiki/`. The three-layer pattern
(raw → wiki → schema) is what matters; the exact folder layout adapts
to the project's needs.

## Conventions

- **ALL CAPS** for tool-discovered files: `AGENTS.md`, `CLAUDE.md`, `SKILL.md`
- **lowercase** for wiki content: `index.md`, `log.md`, `overview.md`
- **`YYYY-MM-DD_slug.ext`** for raw source filenames
- **`[ref: path]`** for source citations in wiki pages
- **`## [YYYY-MM-DD] op | Title`** for log entries

## Tool-Specific Config

Tool-specific configuration lives outside `~/.agents/`:

- OpenCode: `~/.config/opencode/AGENTS.md` (tool schema + references this file)
- Claude Code: `~/.claude/CLAUDE.md` (can `@~/.agents/AGENTS.md`)
- Each tool has its own config directory per XDG conventions

OpenCode-specific instructions are in `~/.config/opencode/AGENTS.md`; OpenCode
uses XDG config paths and does not use `~/.opencode/config/AGENTS.md`. This
file is also listed in `~/.config/opencode/opencode.json` under `instructions`
so OpenCode loads the tool-agnostic system schema automatically.
