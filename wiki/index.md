# Wiki Index

Master routing table. Agent: read this first to find relevant pages.

**Architecture:** raw/ → wiki/ (one-way compile). See [[raw/README]] for source discipline.

## Overview
- [[overview]] — High-level synthesis of the entire wiki: themes, active projects, knowledge gaps

## Projects
<!-- Add per-project pages here as you initialize them with `oc --init-project` -->
<!-- Example: [[my-project]] — Brief description -->

## Domain Knowledge
(none yet — cross-project facts will accumulate here)

## Language Conventions
- [[cpp]] — C++ conventions and best practices

## Proven Patterns
- [[rcu-cached-resource]] — RCU-style CachedResource<T,Token> for hot-reloadable read-heavy data
- [[boost-asio-beast-http]] — Coroutine-based async HTTP server using Boost.Asio + Beast
- [[docker-static-scratch]] — Multi-stage Docker build producing minimal static binary on scratch image

## Concepts
- [[karpathy-llm-wiki]] — Karpathy's LLM Wiki pattern: wiki beats RAG for personal knowledge management
- [[occams-code-setup]] — Architecture: two-config system, presets, agents, fallback, council, skills, scripts
- [[agent-roles-and-models]] — Per-agent design rationale, delegation strategy, model selection, temperature/MCP
- [[oc-launcher]] — Boot sequence, session modes, permissions, memory sync profiles
- [[troubleshooting]] — Common failure modes, diagnostic commands, known-bad models

## Entities
(none yet — add entity pages for people, orgs, tools you use)

## Source Summaries
(none yet — auto-populated by `oc --ingest-repo` and manual ingestion)

## Raw Sources
- [[raw/README]] — Immutable source materials (articles, repos, docs, papers). Wiki compiles from here.
- Raw subfolders: `articles/`, `papers/`, `repos/`, `docs/`, `forums/`, `assets/`, `_inbox/`

## Comparisons
(none yet — add comparison pages when analyzing alternatives)
