---
name: lecture-notes
description: >
  Transform recorded lectures, talks, and presentations into comprehensive, structured
  Obsidian notes. Multi-phase pipeline: transcription (local whisper.cpp), scene detection
  (ffmpeg), AI semantic segmentation, audio-visual fusion, per-episode AI scouting (vision
  LLM), selective OCR, note composition, and quality review. Captures everything: slides,
  formulas (LaTeX), diagrams, speaker commentary, examples, emphasis, annotations, and
  interactive video timestamps. Use when the user has a video file and wants detailed
  study notes, or says "create notes", "make lecture notes", "transcribe and analyze",
  or provides a video with intent to study/document it. Do not use for audio-only content
  — that requires audio-analysis instead.
compatibility: >
  Requires: transcribe (whisper.cpp local), ffmpeg, lecture-scenes.py, OPENROUTER_API_KEY
  (vision LLM — Gemini Pro via OpenRouter). Output is Obsidian-flavored markdown using
  wikilinks, callouts, LaTeX, Media Extended #t= timestamps.
---

# Lecture Notes Pipeline

8-phase pipeline. **Orchestrator drives all phases.** Transcript is the spine — semantic
structure comes from spoken content. Visuals are precision enhancements. Full reference:
`~/wiki/raw/user/docs/2026-05-03_lecture-notes-workflow.md`

```
Phase 0: Assessment      (1-2 min, free)     → Orchestrator
Phase 1: Transcription   (~8 min, free)      → transcribe
Phase 2: Scene Detection (1-2 min, free)     → lecture-scenes.py
Phase 3: Semantic Seg.   (30s, ~$0.001)      → @oracle
Phase 4: Audio-Visual    (<1s, free)         → Orchestrator
Phase 5: AI Scouting     (30-60s, ~$0.01)    → @observer (vision)
Phase 6: Selective OCR   (2-3 min, ~$0.01)   → @observer (parallel)
Phase 7: Composition     (10-15 min)          → Orchestrator + @fixer
Phase 8: Review          (2-3 min, ~$0.001)  → @oracle
```

**Per 60-min lecture:** ~25 min runtime, ~$0.02 cost (transcription is free/local).

---

## Quality Gates (Must Pass Before Proceeding)

| Phase | Gate |
|-------|------|
| **0** | Archetype identified. Output directory + language confirmed with user. |
| **1** | Transcript coherent (check head/tail 40 lines). SRT copied alongside source video. |
| **2** | 10-30 scenes. `scenes.json` valid. All keyframes exist. |
| **3** | 5-15 sections. No time gaps >2s. Every section has ≥1 key_quote. |
| **4** | Every section matched to scene (or `has_visual: false`). Misalignments resolved. |
| **5** | Every episode has `speaker_added`. `needs_ocr` flags set for text/formula slides. |
| **6** | Every `needs_ocr` slide has complete, verified OCR. LaTeX syntax validated. |
| **7** | All sections present. All images exist. All LaTeX valid. Frontmatter complete. |
| **8** | AI review: zero critical, zero major issues. |

If phase fails gate 3 times: flag for human review, continue best-effort with incomplete sections marked.

---

## Phase 0: Assessment

```bash
ffprobe -v error -show_entries format=duration,format_name,size -of json video.mp4

# 6 frames at 30s intervals:
ffmpeg -i video.mp4 -vf "fps=1/30" -vframes 6 -q:v 3 /tmp/sample_%02d.jpg
```

**Delegate to @observer** with the 6 frames:

> Classify each frame: slides, whiteboard/chalkboard, talking-head/webcam,
> screencast/code, mixed, or other. Answer:
> 1. Speaker visible on camera?
> 2. Slides primary visual? (yes/mostly/sometimes/no)
> 3. Handwriting/drawing present?
> 4. Language of visible text?
> 5. Diagrams/charts/code visible?
> 6. Consistent template/branding?
> 7. Mostly OCR (text-heavy) or mostly description (diagrams/whiteboard)?

**Archetype → pipeline parameters:**

| Archetype | Scene threshold | Special |
|-----------|:---:|---|
| Slide-heavy | 0.30 | Standard |
| Whiteboard | 0.15 | Continuous frames, no scene boundaries |
| Screencast | 0.10 | Code blocks, syntax preservation |
| Talking head | Skip Phase 2 | Transcript-driven, no visuals |
| Mixed | 0.30 | Per-episode classification handles it |

**Before proceeding:** Ask user: "Where should I save the output notes? Which language (sr/en/...)?"

---

## Phase 1: Transcription

```bash
transcribe video.mp4 --language LANG
# Verify:
head -40 video.srt && tail -40 video.srt
# Media Extended subtitle auto-detect:
cp video.srt "/path/alongside/source/video.srt"
```

Always use explicit `--language` for non-English. GPU (Vulkan): ~8x realtime.

---

## Phase 2: Visual Segmentation

```bash
python3 ~/.config/opencode/scripts/lecture-scenes.py video.mp4 -t THRESHOLD -o OUTPUT_DIR
# → scenes.json + keyframes/frame_XX.jpg
```

Uses threshold from Phase 0. Fallback to periodic sampling if <5 scenes. Caps at 40.
10-30 scenes for 60-min lecture is ideal. Tune threshold if outside range.

---

## Phase 3: Semantic Segmentation

**Delegate to @oracle.** Send full SRT (Gemini handles 1M tokens easily).

Prompt:

> Below is a complete SRT transcript of a lecture. Extract its thematic structure as JSON.
>
> ```json
> {
>   "lecture": {
>     "title": "Inferred/stated title",
>     "speaker": "Name if mentioned",
>     "duration_seconds": N,
>     "language": "xx"
>   },
>   "sections": [
>     {
>       "section_id": 1,
>       "title": "Short descriptive title (source language)",
>       "start_time": "00:00:00",
>       "end_time": "00:12:30",
>       "start_seconds": 0,
>       "end_seconds": 750,
>       "summary": "2-3 sentence summary",
>       "topics": ["..."],
>       "concepts_introduced": ["new concepts in this section"],
>       "formulas_mentioned": ["formula descriptions"],
>       "key_quotes": [{"time": "HH:MM:SS", "text": "exact quote"}],
>       "emphasis_markers": [{"time": "HH:MM:SS", "note": "speaker emphasizes"}],
>       "examples": [{"time": "HH:MM:SS", "description": "concrete example"}],
>       "slide_references": [{"time": "HH:MM:SS", "context": "points to slide"}],
>       "transitions": ["bridging language to next section"],
>       "questions_asked": [{"time": "HH:MM:SS", "question": "..."}],
>       "tangential_notes": ["interesting digression"]
>     }
>   ],
>   "global_tags": ["..."],
>   "references_mentioned": [{"type": "book|paper|url", "citation": "..."}]
> }
> ```
>
> RULES:
> - EXACT timestamps from SRT. Do not invent.
> - start_time/end_time = first/last cue in section.
> - key_quotes: 1-3 per section. Best core-idea sentences.
> - emphasis_markers: repetitions, "important"/"remember", vocal emphasis moments.
> - slide_references: "as you can see", "this formula here", "look at this diagram".
> - concepts_introduced: what is NEW in this section.
> - Keep titles/summaries in transcript's language.
> - This SRT is the ONLY input. Do not hallucinate.
>
> [FULL SRT]

**Output:** `sections.json`. Validate: 5-15 sections, no gaps >2s, ≥1 key_quote per section.

---

## Phase 4: Audio-Visual Fusion

Orchestrator performs (computation, no AI). For each section in `sections.json`,
find the scene from `scenes.json` with the largest time-window overlap.
Build `episodes.json`:

```json
[
  {
    "episode_id": 1,
    "section": { /* section from sections.json */ },
    "scene": { /* matched scene from scenes.json */ },
    "keyframe": "keyframes/frame_03.jpg",
    "transcript_excerpt": "[SRT lines within section time window, with timestamps]"
  }
]
```

**Misalignments:**
- Speaker introduces topic before slide → extend excerpt backward (5-15s)
- Slide changes mid-sentence → extend to next sentence boundary
- No visual (talking head) → `"has_visual": false`

---

## Phase 5: Per-Episode AI Scouting

**Delegate to @observer. ONE batch call with all episodes.** Saves overhead, preserves context.

> You are analyzing a recorded lecture. I will give you episodes — each with a
> keyframe image and the transcript excerpt from that time window.
>
> For each episode:
>
> 1. `slide_content`: Everything visible on the image — text, formulas, diagrams,
>    charts, annotations, layout, branding.
>
> 2. `content_type`: text_slide | formula_slide | diagram_slide | code_slide |
>    mixed_slide | whiteboard | talking_head | screencast | title_slide | blank
>
> 3. `needs_ocr`: TRUE if slide needs precise text/formula extraction, FALSE if
>    general description is sufficient.
>
> 4. `speaker_added` (MOST VALUABLE): What did the speaker say about this slide
>    that is NOT visible on it? Explanations, examples, intuition, caveats,
>    applications, stories, connections, "this is important" moments.
>
> 5. `connections`: Continuation / builds on previous / new topic / complete shift?
>
> 6. `best_frame_advice`: Best keyframe, or N seconds earlier/later?
>
> 7. `annotations`: Handwritten marks, arrows, underlines added by speaker.
>    Describe content, position, color.
>
> 8. `completeness`: Episode feel complete? More on this topic next?
>
> Return JSON array, one object per episode, preserving episode IDs.
>
> EPISODE 1:
> Image: [keyframe_01.jpg]
> Transcript:
> [00:05:23] ...
> ...
>
> EPISODE 2:
> Image: [keyframe_02.jpg]
> Transcript:
> ...

**Output:** `episodes_analyzed.json`. Validate: every episode has `speaker_added`.

---

## Phase 6: Selective Deep OCR

**Delegate to @observer. Send ALL `needs_ocr` slides in PARALLEL calls.**

> Read the image at `keyframes/frame_XX.jpg`. Extract ALL text and formulas.
> Formulas: LaTeX (block $$...$$, inline $...$). Tables: markdown. Diagrams: describe.
>
> The speaker said about this slide: '[SPEAKER_ADDED]'. Use this context.
>
> Pay attention to: Greek letters as \alpha, \sum (not Unicode), subscripts (x_i not xi),
> superscripts (x^2 not x2), fractions (\frac{a}{b} not a/b), integrals with limits.
> Language: [LANGUAGE].

**Save each as `ocr_results/frame_XX.txt`** with structured sections:
`## Text`, `## Formulas (LaTeX)`, `## Diagrams`, `## Tables`, `## Annotations`.

**Verify:** Greek letters correct, subscripts/superscripts placed, fractions formatted,
multi-line equations preserved, tables complete.

---

## Phase 7: Note Composition

**Agent:** Orchestrator (integration). @fixer for per-section parallel drafting if 10+ sections.

### File structure

```
OUTPUT_DIR/
└── Lecture Title/
    ├── Lecture Title.md
    ├── transcript.srt
    ├── keyframes/
    ├── slides/          ← selected frames copied from keyframes
    └── ocr_results/
```

### Note format

**Frontmatter:**
```yaml
---
title: "Lecture Title"
date: YYYY-MM-DD
speaker: Full Name
duration: "HH:MM:SS"
language: "xx"
tags: [topic1, topic2]
source_video: "path/to/video.mp4"
source_transcript: "transcript.srt"
type: lecture-notes
---
```

**Header (foldable callout):**
```markdown
# Lecture Title

> [!info]- Video & Metadata
> ![[path/to/video.mp4|350]]
> | **Speaker** | Name | **Date** | YYYY-MM-DD |
> | **Duration** | XX min | **Language** | Language |
```

**Per-section (between sections: `---`):**
```markdown
## Section Title

[[path/to/video.mp4#t=12:30|▶ 12:30 – 25:00]]

![[slides/slide_03.jpg|400]]

[OCR text + LaTeX formulas + tables]

> [!note] Speaker's Explanation
> [What the speaker said NOT on the slide — the most valuable part]

> [!warning] Emphasis
> [When speaker stressed this point]

> [!tip] Practical Example
> [Concrete example with full context]

> [!info] Connection
> [How this builds on / connects to other sections]
```

### Callout semantics

| Callout | When | | Callout | When |
|---------|------|-|---------|------|
| `note` | Speaker's explanation | | `important` | Critical/counter-intuitive |
| `warning` | Emphasis, exam-relevant | | `question` | Questions posed |
| `tip` | Examples, code, illustrations | | `danger` | Common mistakes, pitfalls |
| `info` | Connections, references | | `abstract` | Section index |

### Rules

1. `#t=start` only (no `,end`) — avoids locked playback
2. Images at 400px width (`|400`)
3. LaTeX: `$$...$$` block, `$...$` inline. Always commands (`\alpha`), never Unicode (α)
4. All underscores inside `$...$` or `$$...$$`
5. End with `## Summary` + `## Links & References`

### Post-composition checklist

Verify all sections present, all images exist, all LaTeX valid, frontmatter complete,
summary + links present.

---

## Phase 8: Review

**Delegate to @oracle:**

> Review `Lecture Title.md`. Check:
>
> **Structural:** All sections present? Order logical? Timestamps correct?
> **Mathematical:** LaTeX syntax + semantics correct? Match OCR source?
> **Visual:** Every embedded image exists? Correct image per section?
> **Content:** All key_quotes represented? Emphasis visible? Thin sections?
> **Markdown:** Unescaped underscores? Valid wikilinks? `#t=` syntax correct?
> **Completeness:** Summary? Links? Frontmatter?
>
> Report by category. Severity: critical, major, minor, cosmetic.

Apply fixes. Re-run review if critical. **Gate: zero critical, zero major.**

---

## Edge Cases

| Case | Adjustment |
|------|-----------|
| **Whiteboard** | Threshold 0.15. Sequential frames. "Handwritten content" in OCR prompt. |
| **Screencast** | Threshold 0.10. Code blocks with language annotation (```python). |
| **Talking head** | Skip Phase 2, 5, 6. Transcript-driven. Heavier on quotes. |
| **Non-English** | Explicit `--language` in Phase 1. OCR prompts specify language + script. |
| **Poor audio** | Re-transcribe with `ffmpeg -af "highpass=f=200,lowpass=f=3000,afftdn"`. Mark sections `> [!warning] Audio poor`. |
| **Animations** | Threshold 0.40 to avoid false boundaries. Use most complete frame. |
| **Multi-video** | Process parts independently through Phase 6. Merge in Phase 7. `[[part1.mp4#t=...]]` per source. |

---

## Agent Ecosystem

### Delegation map

| Phase | Agent | Why |
|-------|-------|-----|
| 0 | Orchestrator | Decision-making, local tools |
| 1 | Orchestrator | Runs transcribe, verifies output |
| 2 | Orchestrator | Runs lecture-scenes.py |
| 3 | @oracle | Structured JSON from transcript |
| 4 | Orchestrator | Computation only |
| 5 | @observer | Vision + text fusion (audio+visual together) |
| 6 | @observer (parallel) | OCR, independently parallelizable |
| 7 | Orchestrator + @fixer | Integration + per-section drafting |
| 8 | @oracle | Quality review |

### Skills loaded

- **Orchestrator:** `lecture-notes` (this), `audio-analysis` (transcribe details)
- **Observer:** `lecture-notes` (knows output fields expected), `video-analysis` (model options)

### Obsidian integration

- **Check:** If output dir is in an Obsidian vault → verify Media Extended plugin.
  If missing: warn user. Timestamps will be plain links. All else (callouts, LaTeX,
  wikilinks, embeds) work with core Obsidian.
- **SRT subtitles:** Copy `transcript.srt` alongside source video file → Media Extended
  auto-detects and shows interactive subtitles during playback.
