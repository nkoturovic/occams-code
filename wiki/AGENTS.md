# LLM Wiki Schema — Agent Instructions

## What This Is
A persistent, compounding knowledge base maintained by the LLM.
You (the LLM) write and maintain all wiki pages.
The human provides sources, asks questions, and curates.

## Three-Layer Architecture

```
raw/          ← Immutable source documents. NEVER modify.
wiki/         ← LLM-generated wiki. You own this entirely.
AGENTS.md     ← This schema. You follow these rules.
```

### Layer 1: Raw Sources
- Articles, papers, repos, data files, images
- The human drops these in (via Web Clipper, repomix, etc.)
- You READ from them but NEVER write to them
- This is the source of truth — always traceable

#### Raw Taxonomy Policy (Karpathy-aligned)

Keep `raw/` categorization shallow. Semantic organization lives in `wiki/`, not in deep folder trees.

Classification rules:
- Web articles/blog posts/clipped pages → `raw/articles/`
- Papers/preprints/whitepapers → `raw/papers/`
- Repomix dumps/repo archives → `raw/repos/`
- Forum threads (HN/Reddit/Discord exports) → `raw/forums/`
- Docs/RFCs/API refs/datasheets → `raw/docs/`
- Binary/non-text attachments → `raw/assets/`
- Ambiguous or bulk drops awaiting triage → `raw/_inbox/`

Rules:
- DO NOT create extra topic subfolders under `raw/`
- DO NOT edit files in `raw/`
- Prefer filenames: `YYYY-MM-DD_slug.ext`
- Once a source is ingested, keep filename/path stable

### Layer 2: The Wiki
- LLM-generated markdown files: summaries, concepts, entities, comparisons
- You create pages, update them when new sources arrive
- You maintain cross-references and consistency
- The human reads it; you write it

### Layer 3: The Schema (this file)
- Tells you how the wiki is structured
- Defines conventions, workflows, and page formats
- Co-evolved over time with the human

## Directory Structure

```
~/wiki/
├── AGENTS.md              ← This schema (YOU follow these rules)
├── index.md               ← Master catalog. Update on every change.
├── log.md                 ← Append-only activity log.
├── overview.md            ← High-level synthesis of the entire wiki.
│
├── raw/                   ← IMMUTABLE source documents
│   ├── articles/          ← Clipped web articles
│   ├── papers/            ← Academic papers, PDFs
│   ├── repos/             ← Repomix dumps, code archives
│   ├── forums/            ← Forum posts, discussions
│   ├── docs/              ← Library docs, datasheets
│   └── assets/            ← Downloaded images, attachments
│
└── wiki/                  ← LLM-generated wiki (YOU own this)
    ├── projects/          ← Per-project knowledge (ISOLATED)
    ├── domain/            ← Cross-project factual knowledge
    ├── languages/         ← Coding conventions per language
    ├── patterns/          ← Proven reusable patterns
    ├── concepts/          ← Concept pages (general knowledge)
    ├── entities/          ← Entity pages (people, orgs, tools)
    ├── sources/           ← Source summaries
    └── comparisons/       ← Comparison pages
```

## Page Conventions

Every wiki page MUST have YAML frontmatter:

```yaml
---
summary: "One-line description"
type: concept | entity | source-summary | comparison | project
tags: [relevant, tags]
sources: [raw/files referenced]
related: [[wiki pages linked]]
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
---
```

After frontmatter:
- One-line summary in prose
- Content organized by topic
- `[[wikilinks]]` for cross-references
- "References" section at bottom with [ref: source] citations

**Note:** Wiki pages use the frontmatter schema defined above. Do not substitute generic Obsidian properties (`title`, `aliases`, `cssclasses`) for the wiki schema fields.

## Core Workflows

### 1. Ingest (when human adds a source)
When the human says "ingest [filename]":
1. Read the source file in raw/
2. Discuss key takeaways with the human
3. Create/update a summary page in wiki/sources/
4. Update wiki/index.md
5. Update all relevant concept, entity, and domain pages
6. Flag any contradictions with existing wiki content
7. Append an entry to wiki/log.md

A single source might touch 10-15 wiki pages. Stay involved — discuss emphasis with the human before making changes.

### 2. Query (when human asks a question)
1. Read wiki/index.md to find relevant pages
2. Read those pages
3. Synthesize an answer with [[wiki-link]] citations
4. If the answer is valuable, offer to file it as a new wiki page
5. Good answers become permanent wiki pages — this is how explorations compound

### 3. Lint (periodic health check)
When the human says "lint":
1. Check for contradictions between pages
2. Find orphan pages with no inbound links
3. List concepts mentioned but lacking their own page
4. Check for stale claims superseded by newer sources
5. Suggest questions to investigate next
6. Report findings only — do NOT make changes without approval

## Writing Rules

### References are mandatory
Every factual claim must cite its source:
- Code: [ref: src/connection.py:L142]
- GitHub issues: [ref: owner/repo#87]
- Web: [ref: stackoverflow.com/q/12345]
- Own discovery: [ref: session YYYY-MM-DD]
- No source: [unverified]

### Before creating or modifying pages
- ALWAYS ask the human for approval first
- Check if an existing page should be updated instead of creating new
- After any change: update index.md AND append to log.md

### Promotion Protocol
Knowledge starts project-scoped. Promote to global (domain/ or patterns/) ONLY when:
- Validated in 3+ projects
- Human explicitly approves
- Promoted page lists which projects validated it

## Navigation Protocol

### When working on a project:
1. Read index.md first
2. Match project name to wiki/projects/<name>/
3. LOAD: project pages + domain/ + languages/ + patterns/
4. DO NOT LOAD: other projects' pages

### When maintaining the wiki:
1. Read everything for health checks
2. Update index.md after every change
3. Append to log.md with consistent prefix: `## [YYYY-MM-DD] operation | Title`

## Log Format

Each entry starts with a consistent prefix for grep-ability:

```
## [2026-04-08] ingest | Article Title
Source: raw/articles/filename.md
Pages created: sources/summary.md
Pages updated: concepts/topic.md
Notes: Key observations

## [2026-04-08] query | Question asked
Pages read: concepts/topic.md
Output: Filed as comparisons/analysis.md

## [2026-04-08] lint | Health check
Contradictions: 0
Orphan pages: 2
Missing pages: 3
```

## Tool Integration

### defuddle (for web page ingestion)
```bash
defuddle parse <url> --md -o ~/wiki/raw/articles/YYYY-MM-DD_slug.md
```

### qmd (when wiki grows beyond ~200 pages)
```bash
npm install -g @tobilu/qmd
qmd collection add ~/wiki --name my-wiki
qmd query "search term"  # Hybrid BM25 + vector + LLM re-ranking
qmd mcp                  # Start as MCP server
```

### Repomix (for ingesting repos)
```bash
repomix --remote owner/repo -o ~/wiki/raw/repos/repo.xml
```

### GitHub CLI (for ingesting issues)
```bash
gh issue list --repo owner/repo --state closed --limit 200 \
  --json number,title,body > ~/wiki/raw/repos/repo-issues.json
```

## The Compounding Principle

The wiki is a persistent, compounding artifact. Every source ingested and every question asked makes it richer. Knowledge is compiled once and kept current — not re-derived on every query.

**Obsidian is the IDE. The LLM is the programmer. The wiki is the codebase.**
