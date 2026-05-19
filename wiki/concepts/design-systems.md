---
summary: "DESIGN.md files: plain-text design systems that AI agents read to generate pixel-perfect, brand-consistent UI"
type: concept
tags: [design, ui, ux, design-md, agent, voltagent]
sources:
  - 2026-04-10_voltagent--awesome-design-md
related:
  - occams-code-setup
  - agent-roles-and-models
  - vision-integration
created: 2026-04-10
updated: 2026-04-10
confidence: high
---

# DESIGN.md — Plain-Text Design Systems for AI Agents

## What It Is

[DESIGN.md](https://stitch.withgoogle.com/docs/design-md/overview/) is a plain-text design system document that AI agents read to generate consistent, brand-accurate UI. It's just a markdown file — drop it in your project root and any AI agent instantly understands how your UI should look.

| File | Who reads it | What it defines |
|------|-------------|-----------------|
| `AGENTS.md` | Coding agents | How to **build** the project |
| `DESIGN.md` | Design agents | How the project should **look and feel** |

This is the design equivalent of AGENTS.md. Where AGENTS.md tells the agent your conventions and rules, DESIGN.md tells it your colors, typography, spacing, component styles, and visual philosophy.

## Why It Matters

Without a DESIGN.md, the designer agent uses generic defaults — "make it look modern and clean." Results vary wildly between sessions and agents.

With a DESIGN.md, you get **pixel-perfect, brand-consistent UI** every time. The agent reads exact hex colors, font sizes with letter-spacing values, shadow systems, component states (hover, focus, disabled), and responsive breakpoints. The output matches the design system, not the model's imagination.

## The 9-Section Format

Every DESIGN.md follows this structure (from the [Stitch format](https://stitch.withgoogle.com/docs/design-md/format/)):

| # | Section | What it contains | Why the agent needs it |
|---|---------|-----------------|----------------------|
| 1 | Visual Theme & Atmosphere | Mood, density, design philosophy | Sets the creative direction before any code |
| 2 | Color Palette & Roles | Semantic name + hex + functional role | Agent picks the right color for the right purpose |
| 3 | Typography Rules | Font families, size/weight/spacing hierarchy table | Exact values — no guessing at "large heading" |
| 4 | Component Stylings | Buttons, cards, inputs, nav with states | Consistent interactive elements across all pages |
| 5 | Layout Principles | Spacing scale, grid system, whitespace rules | Structural consistency, not just visual |
| 6 | Depth & Elevation | Shadow system, surface hierarchy | Cards float at the right level, modals layer correctly |
| 7 | Do's and Don'ts | Design guardrails, anti-patterns | Prevents common mistakes the agent would otherwise make |
| 8 | Responsive Behavior | Breakpoints, touch targets, collapsing rules | Works on mobile without separate specs |
| 9 | Agent Prompt Guide | Quick color reference, ready-to-use prompts | Shortcut for common requests |

Each file is ~300 lines (~3000 tokens) — detailed enough for precision, concise enough for the agent's context window.

## How to Get One

### From the awesome-design-md collection (62 brands)

[awesome-design-md](https://github.com/VoltAgent/awesome-design-md) provides ready-to-use DESIGN.md files extracted from real websites. Use the CLI:

```bash
# Install a design system into your project
npx getdesign@latest add vercel          # creates ./DESIGN.md
npx getdesign@latest add stripe          # creates ./stripe/DESIGN.md
npx getdesign@latest add linear.app      # creates ./linear.app/DESIGN.md
npx getdesign@latest add apple --force   # overwrites existing DESIGN.md

# List all available brands
npx getdesign@latest list
```

Available brands include: Vercel, Stripe, Linear, Apple, Notion, Figma, Airbnb, Tesla, Spotify, Supabase, Framer, SpaceX, Uber, IBM, BMW, Ferrari, Coinbase, Sentry, PostHog, and 40+ more.

### Write your own

Create a `DESIGN.md` in your project root following the 9-section format above. Even a partial file (just colors + typography) dramatically improves output consistency.

## How the Designer Agent Uses It

When DESIGN.md exists in the project root, the designer agent (@designer) reads it automatically. No special configuration needed.

**Workflow:**

1. Pick a design: `npx getdesign@latest add <brand>`
2. Tell the agent: "Build a landing page following the design system in DESIGN.md"
3. Get pixel-perfect output matching the brand's actual design system

**Example prompts that work well with DESIGN.md:**
- "Create a pricing page using the design system in DESIGN.md"
- "Build a dashboard sidebar component following DESIGN.md's component styles"
- "Redesign this page to match the typography and color palette in DESIGN.md"
- "Create a responsive hero section using DESIGN.md's spacing scale and breakpoints"

## Design Selection Guide

### For developer tools & SaaS:
- **Vercel** — Black and white precision, Geist font, monochrome minimalism
- **Linear** — Ultra-minimal dark UI, purple accent, precise engineering aesthetic
- **Raycast** — Sleek dark chrome, vibrant gradient accents
- **Warp** — Dark IDE-like, block-based command UI

### For premium/consumer brands:
- **Apple** — Premium white space, SF Pro, cinematic imagery
- **Tesla** — Radical subtraction, cinematic full-viewport photography
- **Stripe** — Signature purple gradients, weight-300 elegance

### For dashboards & data-heavy UIs:
- **Sentry** — Dark dashboard, data-dense, pink-purple accent
- **PostHog** — Playful branding, developer-friendly dark UI
- **ClickHouse** — Yellow-accented, technical documentation style

### For landing pages & marketing:
- **Airbnb** — Warm coral accent, photography-driven, rounded UI
- **Notion** — Warm minimalism, serif headings, soft surfaces
- **Framer** — Bold black and blue, motion-first, design-forward

### For fintech:
- **Stripe** — Purple gradients, premium feel
- **Revolut** — Sleek dark, gradient cards, fintech precision
- **Coinbase** — Clean blue identity, trust-focused

## Integration with Occam's Code

No special setup required. The designer agent automatically reads any DESIGN.md in the project root. This works because:

1. The orchestrator delegates UI/UX work to the designer agent
2. The designer agent reads files from the project directory, including DESIGN.md
3. DESIGN.md is plain markdown — no parsing or special tooling needed

**Tip:** For best results, reference DESIGN.md explicitly in your prompt to the agent. The agent may not proactively check for DESIGN.md unless prompted.

## Related
- [[occams-code-setup]] — Architecture and agent configuration
- [[agent-roles-and-models]] — Designer agent role and capabilities
- [[vision-integration]] — Vision integration for image-based design workflows
