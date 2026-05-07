---
name: lecture-notes
description: >
  Transform recorded lectures, talks, and presentations into comprehensive, structured
  Obsidian notes. Multi-phase pipeline: transcription (local whisper.cpp), scene detection
  (ffmpeg), AI semantic segmentation, audio-visual fusion, per-segment AI scouting (vision
  LLM), selective OCR, note composition, and quality review. Captures everything: slides,
  formulas (LaTeX), diagrams, speaker commentary, examples, emphasis, annotations, and
  interactive video timestamps. Use when the user has a video file and wants detailed
  study notes, or says "create notes", "make lecture notes", "transcribe and analyze",
  or provides a video with intent to study/document it. Do not use for audio-only content
  — that requires audio-analysis instead.
compatibility: >
  Requires: transcribe (whisper.cpp local), ffmpeg, lecture-scenes.py, lecture-fusion.py,
  lecture-clips.py, OPENROUTER_API_KEY (vision LLM via OpenRouter). Output is
  Obsidian-flavored markdown using wikilinks, callouts, LaTeX, Media Extended #t= timestamps.
---

# Lecture Notes Pipeline

9-phase pipeline. **Orchestrator drives all phases.** Transcript is the spine — semantic
structure comes from spoken content. Visuals are precision enhancements.

**Execution: first create a todo list with all 9 phases (1–9). Pass each phase's quality
gate before proceeding to the next. Do not skip any phase. Adapt each phase's parameters
to the lecture — archetype from Phase 1, language from user, merge duration from content
type. Generic defaults produce generic notes.**

```
Phase 1: Assessment      (1-2 min)           → Orchestrator
Phase 2: Transcription   (~8 min)            → transcribe
Phase 3: Scene Detection (1-2 min)           → lecture-scenes.py
Phase 4: Semantic Seg.   (~30s)              → @oracle
Phase 5: Segment Prep.    (~1s)               → lecture-fusion.py + lecture-clips.py
Phase 6: AI Scouting     (1-2 min)           → @observer (video)
Phase 7: Selective OCR   (2-3 min)           → @observer (parallel)
Phase 8: Composition     (10-15 min)          → Orchestrator + @fixer
Phase 9: Review          (2-3 min)           → @oracle
```

**Per 60-min lecture:** ~25 min runtime (transcription is free/local).

---

## Quality Gates (Must Pass Before Proceeding)

| Phase | Gate |
|-------|------|
| **1** | Archetype identified. Output directory + language confirmed with user. |
| **2** | Transcript coherent (head/tail 40 lines). SRT copied alongside source video and copy verified. |
| **3** | 12-60 scenes. max_duration < total/2, median < total/8. `scenes.json` valid. All keyframes exist. |
| **4** | 5-15 sections. No time gaps >2s. Every section has ≥1 key_quote. |
| **5** | Every section matched to scene (or `has_visual: false`). Misalignments resolved. Every section has a clip OR a `clip_status` explaining why not. No clip exceeds 20MB. All `clip_status: "ok"` clips playable. |
| **6** | Every segment has `speaker_added` AND `speaker_emphasis` (≥1 per video segment). `slide_content` describes progression. Keyframe-fallback segments require `speaker_added` only. `needs_ocr` flags set for text/formula slides. |
| **7** | Every `needs_ocr` slide has complete, verified OCR. LaTeX syntax validated. `speaker_emphasis` context used to prioritize OCR accuracy. |
| **8** | All sections present. All images exist. All LaTeX valid. Frontmatter complete. `> [!important] Speaker Emphasis` callouts present for emphasized sections. |
| **9** | AI review: zero critical, zero major issues. Video hallucination check: 2-3 segments cross-checked — no fabricated transitions between frames. |

If phase fails gate 3 times: flag for human review, continue best-effort with incomplete sections marked.

---

## Phase 1: Assessment

```bash
ffprobe -v error -show_entries format=duration,format_name,size -of json video.mp4

# 6 frames at 30s intervals:
ffmpeg -i video.mp4 -vf "fps=1/30" -vframes 6 -q:v 3 /tmp/sample_%02d.jpg
```

**Delegate to @observer** with the 6 frames:

> Classify these frames: slides / whiteboard / screencast / talking-head / mixed.
> Which archetype dominates? Speaker visible? Handwriting/drawing present?
> Language of visible text? Text-heavy (OCR needed) or visual (description needed)?

**Archetype → pipeline parameters:**

| Archetype | Scene threshold | Special |
|-----------|:---:|---|
| Slide-heavy | 0.30 | Standard |
| Whiteboard | 0.10 | Continuous frames, no scene boundaries |
| Screencast | 0.10 | Code blocks, syntax preservation |
| Talking head | Skip Phase 3 | Transcript-driven, no visuals |
| Mixed | 0.30 | Per-segment classification handles it |

**If not already specified:** Ask user for output directory and language.

---

## Phase 2: Transcription

```bash
transcribe video.mp4 --language LANG
# Verify:
head -40 video.srt && tail -40 video.srt
# Sibling copy for Media Extended (auto-detected, manual toggle to show):
cp video.srt "/path/alongside/source/video.srt" && test -f "/path/alongside/source/video.srt"
```

Always use explicit `--language` for non-English. GPU (Vulkan): ~8x realtime.
Media Extended auto-detects sibling SRT files.

---

## Phase 3: Visual Segmentation

```bash
python3 ~/.config/opencode/scripts/lecture-scenes.py video.mp4 -t THRESHOLD -o scenes.json
# → scenes.json + keyframes/frame_XX.jpg
```

Uses threshold from Phase 1. Fallback to periodic sampling at 5-minute intervals if gate fails.
Gate: at least floor(duration_min/5) scenes (minimum 12, maximum 60). max scene duration < total/2, median < total/8.
Failed gate → auto-retune (step 0.05, max 3 retries) or best-effort with warning.
Post-detect merge: scenes shorter than `--min-duration` (default 8s) are absorbed into
the previous scene. Archetype-dependent: Slide-heavy 8s (catches cursor flickers),
Whiteboard 4s (preserves incremental writing steps), Screencast 4s (each code block
counts), Mixed 6s. Pass `--min-duration` to `lecture-scenes.py` based on Phase 1 archetype.

---

## Phase 4: Semantic Segmentation

**Delegate to @oracle.** Send full SRT (1M-token context models handle this easily).

Prompt:

> Below is a complete SRT transcript of a lecture. Extract its structure as JSON.
>
> ```json
> {
>   "lecture": {
>     "title": "Inferred/stated title",
>     "speaker": "Name if mentioned",
>     "language": "xx"
>   },
>   "sections": [
>     {
>       "section_id": 1,
>       "title": "Short title (source language)",
>       "start_seconds": 0,
>       "end_seconds": 750,
>       "summary": "1-2 sentence summary",
>       "concepts_introduced": ["new concepts"],
>       "key_quotes": ["1-3 best core-idea sentences verbatim"],
>       "content_type": "whiteboard|code|text|mixed"
>     }
>   ],
>   "global_tags": ["topic1", "topic2"]
> }
> ```
> RULES:
> - EXACT timestamps from SRT. start_seconds/end_seconds = first/last cue.
> - 5-15 sections. No time gaps >2s.
> - concepts_introduced: what is NEW in this section.
> - key_quotes: 1-3 per section.
> - content_type: whiteboard (derivations/drawing), code (screen/editor), text (slide-based), mixed.
> - Keep titles/summaries in transcript's language.
> - This SRT is the ONLY input. Do not hallucinate.
>
> [FULL SRT]

**Output:** `sections.json`. Validate: 5-15 sections, no gaps >2s, ≥1 key_quote per section.

---

## Phase 5: Segment Preparation

```bash
python3 ~/.config/opencode/scripts/lecture-fusion.py sections.json scenes.json video.srt -o segments.json
```

The script: for each section, finds the best-matching scene by overlap. Extracts the
best keyframe (largest JPEG — most visual content, avoids blank frames). Pads transcript
excerpt 15s backward, writes self-contained `segments.json`.

`segments.json` carries all data needed by downstream phases — each segment includes:
`segment_id`, full `section` fields, matched `scene`, `keyframe`, `has_visual`,
`global_tags`, `references_mentioned`, and `transcript_excerpt`.
**No separate file join needed at Phase 8.**

**Frame naming:** always variant suffix — `frame_NNNa.jpg` on first use of a scene,
`frame_NNNb.jpg`, `frame_NNNc.jpg` for subsequent sections. Phase 3 scene-midpoint
keyframes (`frame_NNN.jpg`) are never overwritten.

**Misalignments:**
- Speaker introduces topic before slide → excerpt padded 15s backward
- Slide changes mid-sentence → padded 5s forward
- No visual (talking head) → `"has_visual": false`, frame at midpoint as best-effort
- Blank frame detected (JPEG < 50KB) → keyframe discarded, `has_visual: false`

---

### Clip Extraction (Phase 6 video input)

```bash
python3 ~/.config/opencode/scripts/lecture-clips.py segments.json video.mp4 -o clips/
```

Extracts per-section video clips for Phase 6 scouting:

1. Read `start_seconds` and `end_seconds` from `segments.json`
2. Stream-copy clip via ffmpeg (instant, lossless)
3. If clip exceeds 15MB: re-encode at 640px, 0.5 FPS, mono audio
4. If still exceeds 15MB: second-pass at 480px, 0.3 FPS
5. Write `clip_path` and `clip_status` to `segments.json`

**Output:** `clips/section_NN.mp4` + updated `segments.json`.

**Clip status fields:**
- `clip_path`: path to clip (or `null` if extraction failed/skipped)
- `clip_status`: `"ok"` | `"re_encoded"` | `"oversize"` | `"error"` | `"no_visual"`

Phase 6 reads `clip_status` per segment:
- `"ok"` or `"re_encoded"` → send video clip to observer
- `"oversize"`, `"error"`, or `"no_visual"` → fall back to keyframe-only analysis

**Stream-copy note:** ffmpeg `-c copy` seeks to the nearest keyframe before `start_seconds`.
Clips may start up to GOP-size seconds early (typically 2-10s). The 15s backward transcript
padding from Phase 5 already covers this drift — no correctness impact.

---

## Phase 6: Per-Segment AI Scouting (Video-Enhanced)

**Delegate to @observer. Send all sections in PARALLEL calls.** Each section has its own
video clip — no dedup needed (every section has unique time ranges).

For segments where `clip_status` is `"oversize"`, `"error"`, or `"no_visual"`:
fall back to sending the keyframe JPEG + transcript excerpt instead of video.

**Per-segment observer prompt construction:** For each segment, build the prompt by:
1. For video clips (`clip_status: ok` or `re_encoded`): send via `python3 ~/.config/opencode/scripts/analyze-video.py <clip>`. For keyframe-fallback (`clip_status: oversize`, `error`, or `no_visual`): observer uses Read tool on the keyframe JPEG.
2. Injecting `[START_TIME]` and `[END_TIME]` from the segment's `section` fields
3. Including the `transcript_excerpt` from `segments.json`
4. Optionally including the section title for context

Template:

> You are analyzing a recorded lecture. Each segment has a video clip +
> transcript excerpt spanning [START_TIME] to [END_TIME] in the original
> lecture. The video clip is a sub-extract — use transcript timestamps as
> reference. **All time fields (speaker_emphasis.time, slide_content timing
> hints) must use original lecture time, not clip-internal 00:00.**
>
> For each segment:
>
> 1. `slide_content`: What is VISIBLE in the clip. Describe progression
>    thoroughly — all equations, diagrams, annotations visible. Note handwriting
>    appearing on whiteboard, code shown on screen, content building up across
>    frames. Include ~MM:SS timing hints for key transitions
>    (board cleared, formula completed, graph drawn) — approximate within ±5s,
>    useful for sub-section navigation. Anchor to transcript timestamps where
>    possible; estimate from clip position otherwise. Skip if unsure.
>    **ANTI-HALLUCINATION:** describe ONLY
>    what you see in the frames, never invent from transcript.
>
> 2. `content_type`: text | formulas | diagrams | code | whiteboard |
>    talking_head | screencast | title_slide | mixed
>
> 3. `needs_ocr`: TRUE if the section contains important text/formulas that need
>    precise extraction, FALSE if general description is sufficient.
>
> 4. `speaker_added`: What the speaker said about the visible content that
>    is NOT on the slide/board — explanations, intuition, caveats, examples.
>    Draw this from AUDIO. Capture spoken insight, not transcript restatement.
>
> 5. `speaker_emphasis`: Moments where voice indicates importance (slowing
>    down, volume shift, repetition, phrases like "this is important").
>    Format: [{"time": "14:20", "text": "exact quote", "cue": "slows down, repeats"}]
>    Capture 2-5 per section. Become [!important] callouts in notes.
>
> 6. `connection_type`: "opening" | "core" | "application" | "summary" | "transition" —
>    infer from position in lecture and whether speaker introduces new concepts or
>    references earlier material.
>
> 7. `video_note`: Anything the note composer should know — completeness concerns,
>    audio quality, transitions missed by low FPS. (For keyframe-fallback
>    segments, use `image_note` instead.)
>
> Return a JSON object for this segment:
> ```json
> {
>   "segment_id": 1,
>   "keyframe": "frame_01.jpg",
>   "has_visual": true,
>   "slide_content": "...",
>   "content_type": "whiteboard",
>   "needs_ocr": false,
>   "speaker_added": "...",
>   "speaker_emphasis": [{"time": "14:20", "text": "...", "cue": "slows down"}],
>   "connection_type": "core",
>   "video_note": "..."
> }
> ```
> Copy `segment_id`, `keyframe`, and `has_visual` verbatim from the prompt.
> Add your analysis fields alongside them.

> **Assembly:** The orchestrator collects all single-segment observer outputs and wraps them into `segments_analyzed.json`:
> ```json
> { "video": "...", "total_segments": N, "segments": [...] }
> ```

**Output:** `segments_analyzed.json`. Validate: every video segment has `speaker_added`
AND `speaker_emphasis` (≥1 per segment). Keyframe-fallback segments require `speaker_added`
only. Output wrapped in an object matching `segments.json` structure.

**→ GATE: Check `needs_ocr` in segments_analyzed.json. If ANY segment has `needs_ocr: true`, Phase 7 IS REQUIRED for those segments. Do not skip.**

---

## Phase 7: Selective Deep OCR

**Delegate to @observer. Send ALL `needs_ocr` slides in PARALLEL calls.**

> Read the image at `keyframes/frame_XX.jpg`. Extract ALL text and formulas.
> Formulas: LaTeX (block $$...$$, inline $...$). Tables: markdown. Diagrams: describe.
>
> Analyze ONLY this one image. Do NOT include cross-frame comparisons.
>
> The speaker emphasized these parts in this section:
> [SPEAKER_EMPHASIS from Phase 6 — e.g. "Pay attention to boundary conditions" (14:20)]
> Pay special attention to accurately transcribing emphasized content.
>
> The speaker said about this slide: '[SPEAKER_ADDED]'. Use this context.
>
> Pay attention to: Greek letters as \alpha, \sum (not Unicode), subscripts (x_i not xi),
> superscripts (x^2 not x2), fractions (\frac{a}{b} not a/b), integrals with limits.
> Language: [LANGUAGE].

**Save each as `ocr_results/frame_XX.txt`** with these exact section headers —
all five required, even if a section is empty:
```
## Text
## Formulas (LaTeX)
## Diagrams
## Tables
## Annotations
```

**Verify:** Greek letters correct, subscripts/superscripts placed, fractions formatted,
multi-line equations preserved, tables complete.

### Cross-Frame Comparison

When multiple OCR results exist for the same scene (whiteboard variant frames):
compare `## Formulas (LaTeX)` sections. Write `ocr_results/_cross_frame.md` for
differences. Phase 8 uses it to add `> [!important] Correction` callouts.

---

## Phase 8: Note Composition

**Agent:** Orchestrator (integration). @fixer for per-section parallel drafting if 10+ sections.

### File structure

```
OUTPUT_DIR/
└── Lecture Title/
    ├── Lecture Title.md
    ├── transcript.srt
    ├── clips/             ← per-section video clips
    ├── keyframes/
    ├── slides/            ← selected frames copied from keyframes
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

[Write the section's core content here — concepts, derivations, flow — as plain text.]

> <!-- Use callouts selectively — only where segment data warrants. Most sections need 1-2, not all types. -->

> [!note] Speaker's Explanation
> [What the speaker said NOT on the slide — the most valuable part]

> [!warning] Emphasis
> [When speaker stressed this point]

> [!tip] Practical Example
> [Concrete example with full context]

> [!important] Speaker Emphasis
> "Pay attention to boundary conditions" — speaker slows down, repeats (≈14:20)

> [!info] Connection
> [How this builds on / connects to other sections]
```

### Callout semantics

Plain text carries the core content; callouts highlight notable moments.

| Callout | When | | Callout | When |
|---------|------|-|---------|------|
| `note` | Speaker's explanation | | `important` | Speaker emphasis (tone, repetition, "this is key") |
| `warning` | Emphasis, exam-relevant | | `question` | Questions posed |
| `tip` | Examples, code, illustrations | | `danger` | Common mistakes, pitfalls |
| `info` | Connections, references | | `abstract` | Section index |

### Rules

0. Write thorough prose — capture every concept, derivation, and example the speaker covers. Callouts supplement, not replace, the main text.
1. `#t=start` only (no `,end`) — avoids locked playback
2. Images at 400px width (`|400`)
3. LaTeX: `$$...$$` block, `$...$` inline. Always commands (`\alpha`), never Unicode (α)
4. All underscores inside `$...$` or `$$...$$`
5. End with `## Summary` + `## Links & References`

### Connection Synthesis

After drafting all sections, review `segments_analyzed.json` for `connection_type` values across sections. Write `> [!info] Connection` callouts that show how sections build on each other. The orchestrator has full context — identify narrative arcs, prerequisite chains, and thematic groupings the observer (single-segment) could not see.

### Post-composition checklist

Verify all sections present, all images exist, all LaTeX valid, frontmatter complete,
summary + links present.
- Prose thoroughness: every section has substantive plain text (concepts, derivations, flow), not only callout blocks.

---

## Phase 9: Review

**Delegate to @oracle:**

> Review `Lecture Title.md`. Check:
>
> **Structural:** All sections present? Order logical? Timestamps correct?
> **Mathematical:** LaTeX syntax + semantics correct? Match OCR source?
> **Visual:** Every embedded image exists? Correct image per section?
> **Content:** All key_quotes represented? Emphasis visible? Thin sections?
> **Video-specific:** Does `slide_content` describe visible content progression,
> or fabricate transitions between sampled frames? Cross-check 2-3 random
> segments against the actual video. Are `speaker_emphasis` entries grounded
> in audible vocal cues (not inferred from transcript alone)?
>
> Flag keyframe-fallback segments for human review.
> **Markdown:** Unescaped underscores? Valid wikilinks? `#t=` syntax correct?
> **Completeness:** Summary? Links? Frontmatter?
>
> Report by category. Severity: critical, major, minor, cosmetic.

Apply fixes. Re-run review if critical. **Gate: zero critical, zero major.**

---

## Edge Cases

| Case | Adjustment |
|------|-----------|
| **Whiteboard** | Threshold 0.10. Sequential frames. "Handwritten content" in OCR prompt. |
| **Screencast** | Threshold 0.10. Code blocks with language annotation (```python). |
| **Talking head** | Skip Phase 3, 6, 7. Transcript-driven. Heavier on quotes. |
| **Non-English** | Explicit `--language` in Phase 2. OCR prompts specify language + script. |
| **Poor audio** | Re-transcribe with `ffmpeg -af "highpass=f=200,lowpass=f=3000,afftdn"`. Mark sections `> [!warning] Audio poor`. |
| **No audio** | Skip Phase 2. Use periodic sampling in Phase 3. Phases 6/7 become image-only (keyframe-fallback). Heavier reliance on OCR. |
| **Animations** | Threshold 0.40 to avoid false boundaries. Use most complete frame. |
| **Multi-video** | Process parts independently through Phase 7. Merge in Phase 8. `[[part1.mp4#t=...]]` per source. |

---

## Agent Ecosystem

### Delegation map

| Phase | Agent | Why |
|-------|-------|-----|
| 1 | Orchestrator | Decision-making, local tools |
| 2 | Orchestrator | Runs transcribe, verifies output |
| 3 | Orchestrator | Runs lecture-scenes.py |
| 4 | @oracle | Structured JSON from transcript |
| 5 | Orchestrator | Runs lecture-fusion.py + lecture-clips.py |
| 6 | @observer | Vision + text fusion (audio+visual together) |
| 7 | @observer (parallel) | OCR, independently parallelizable |
| 8 | Orchestrator + @fixer | Integration + per-section drafting |
| 9 | @oracle | Quality review |

### Orchestrator Rules

1. **Run all 9 phases in order.** Do not skip any phase. Even "free" phases (2, 3, 5) are required — they produce data consumed downstream.
2. **Phase 6→7 gate:** After Phase 6, scan `segments_analyzed.json` for `needs_ocr: true`. If found, run Phase 7 for those segments. OCR produces exact LaTeX — Phase 8 depends on it for formula-heavy sections.
3. **Phase 6 is parallel:** Send all per-segment clips to @observer simultaneously. Each segment has its own video clip — calls are independent with no shared state.
4. **Phase 7 is parallel:** Send all `needs_ocr` slides to @observer simultaneously. Independent images, no cross-contamination risk.
5. **Quality over speed.** Each phase exists to capture information the next phase depends on. Skipping a phase produces incomplete notes — run all 9 phases regardless of time.
6. **Gate failures → retry or best-effort.** If a phase fails its quality gate 3 times, continue with incomplete sections marked for human review. Never block the pipeline.
7. **Verify outputs before proceeding.** Check file existence, line counts, JSON validity at each phase boundary.
8. **Script errors → fix, don't skip.** If a local script fails (transcribe, lecture-scenes.py, lecture-clips.py), resolve the error first. These are deterministic — failures are fixable, not random.

### Skills loaded

- **Orchestrator:** `lecture-notes` (this), `audio-analysis` (transcribe details)
- **Observer:** `lecture-notes` (knows output fields expected), `video-analysis` (model options)

### Obsidian integration

- **Check:** If output dir is in an Obsidian vault → verify Media Extended plugin.
  If missing: warn user. Timestamps will be plain links. All else (callouts, LaTeX,
  wikilinks, embeds) work with core Obsidian.
- **SRT subtitles:** Copy `transcript.srt` alongside source video file → Media Extended
  auto-detects and shows interactive subtitles during playback.
