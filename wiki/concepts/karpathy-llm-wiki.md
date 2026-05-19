---
summary: "Karpathy's LLM Wiki pattern — wiki beats RAG for personal knowledge management"
type: concept
tags: [karpathy, llm-wiki, knowledge-management, rag, obsidian]
sources: []
related:
created: 2026-04-08
updated: 2026-04-08
confidence: high
---
# Karpathy LLM Wiki Pattern

## Core Idea
Instead of RAG (retrieving from raw documents at query time), the LLM incrementally builds and maintains a persistent wiki — structured, interlinked markdown files that sit between you and raw sources.

**Key insight:** Knowledge is compiled once and kept current, not re-derived on every query.

## Three-Layer Architecture
1. **Raw Sources** (`raw/`) — Immutable. LLM reads but never writes.
2. **The Wiki** (`wiki/`) — LLM-generated. Summaries, concepts, entities, comparisons.
3. **The Schema** (`AGENTS.md`) — Tells LLM how to structure and maintain the wiki.

## Division of Labor
- **Human:** Provides sources, asks questions, curates
- **LLM:** All bookkeeping — summarizing, cross-referencing, filing, maintaining consistency

**Analogy:** Obsidian is the IDE. The LLM is the programmer. The wiki is the codebase.

## Core Operations
1. **Ingest** — Drop source into raw/, LLM reads, discusses, updates 10-15 wiki pages
2. **Query** — Ask questions, LLM searches wiki, synthesizes answer, offers to file it
3. **Lint** — Periodic health check: contradictions, orphans, missing pages, stale claims

## Compounding Effect
- Every source ingested makes the wiki richer
- Every query can generate new wiki pages
- Cross-references are pre-built, not discovered ad-hoc
- Contradictions are flagged during ingestion

## Tool Stack
| Tool | Role |
|------|------|
| Obsidian | IDE/viewer |
| Obsidian Web Clipper | Clip articles to markdown |
| qmd | Local search (200+ pages) |
| Repomix | Pack GitHub repos |
| Git | Version control |

## References
- [Karpathy's original gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Antigravity deep dive](https://antigravity.codes/blog/karpathy-llm-wiki-idea-file)
- [Vannevar Bush's Memex (1945)](https://www.theatlantic.com/magazine/archive/1945/07/as-we-may-think/303881/)
