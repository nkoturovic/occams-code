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

8-phase pipeline. **Orchestrator drives all phases.** Transcript is the spine — semantic
structure comes from spoken content. Visuals are precision enhancements.

```
Phase 0: Assessment      (1-2 min, free)     → Orchestrator
Phase 1: Transcription   (~8 min, free)      → transcribe
Phase 2: Scene Detection (1-2 min, free)     → lecture-scenes.py
Phase 3: Semantic Seg.   (30s, ~$0.001)      → @oracle
Phase 4: Audio-Visual    (<1s, free)         → lecture-fusion.py
Phase 4.5: Clip Extract  (<1s, free)         → lecture-clips.py
Phase 5: AI Scouting     (1-2 min, ~$0.08)   → @observer (video)
Phase 6: Selective OCR   (2-3 min, ~$0.01)   → @observer (parallel)
Phase 7: Composition     (10-15 min)          → Orchestrator + @fixer
Phase 8: Review          (2-3 min, ~$0.001)  → @oracle
```

**Per 60-min lecture:** ~25 min runtime, ~$0.10 cost (transcription is free/local).

---

## Quality Gates (Must Pass Before Proceeding)

| Phase | Gate |
|-------|------|
| **0** | Archetype identified. Output directory + language confirmed with user. |
| **1** | Transcript coherent (head/tail 40 lines). SRT copied alongside source video and copy verified. |
| **2** | 6-60 scenes. max_duration < total/2, median < total/8. `scenes.json` valid. All keyframes exist. |
| **3** | 5-15 sections. No time gaps >2s. Every section has ≥1 key_quote. |
| **4** | Every section matched to scene (or `has_visual: false`). Misalignments resolved. |
| **4.5** | Every section has a clip OR a `clip_status` explaining why not. No clip exceeds 20MB. All `clip_status: "ok"` clips playable. |
| **5** | Every segment has `speaker_added` AND `speaker_emphasis` (≥1 per video segment). `slide_content` describes progression. Keyframe-fallback segments require `speaker_added` only. `needs_ocr` flags set for text/formula slides. |
| **6** | Every `needs_ocr` slide has complete, verified OCR. LaTeX syntax validated. `speaker_emphasis` context used to prioritize OCR accuracy. |
| **7** | All sections present. All images exist. All LaTeX valid. Frontmatter complete. `> [!important] Speaker Emphasis` callouts present for emphasized sections. |
| **8** | AI review: zero critical, zero major issues. Video hallucination check: 2-3 segments cross-checked — no fabricated transitions between frames. |

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
| Mixed | 0.30 | Per-segment classification handles it |

**Before proceeding:** Ask user: "Where should I save the output notes? Which language (sr/en/...)?"

---

## Phase 1: Transcription

```bash
transcribe video.mp4 --language LANG
# Verify:
head -40 video.srt && tail -40 video.srt
# Sibling copy for Media Extended (auto-detected, manual toggle to show):
cp video.srt "/path/alongside/source/video.srt" && test -f "/path/alongside/source/video.srt"
```

Always use explicit `--language` for non-English. GPU (Vulkan): ~8x realtime.

Media Extended detects sibling SRT files. Auto-display of subtitles is plugin-dependent
(best-effort config: `playback.track.default-enabled: true` in plugin data.json,
but known to not work reliably on all versions). User toggles subtitles manually
in the player — one click.

---

## Phase 2: Visual Segmentation

```bash
python3 ~/.config/opencode/scripts/lecture-scenes.py video.mp4 -t THRESHOLD -o OUTPUT_DIR
# → scenes.json + keyframes/frame_XX.jpg
```

Uses threshold from Phase 0. Fallback to periodic sampling if <6 scenes.
Gate: 6-60 scenes, max scene duration < total/2, median < total/8.
Failed gate → auto-retune (step 0.05, max 3 retries) or best-effort with warning.
Post-detect merge: scenes shorter than `--min-duration` (default 8s) are absorbed
into the previous scene. Eliminates presentation flickers, cursor transitions, and
taskbar overlays without losing real content boundaries.

---

## Phase 3: Semantic Segmentation

**Delegate to @oracle.** Send full SRT (1M-token context models handle this easily).

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

```bash
python3 ~/.config/opencode/scripts/lecture-fusion.py sections.json scenes.json video.srt -o segments.json
```

The script: for each section, finds the best-matching scene by overlap. Extracts 3
**candidate frames** at 25%, 50%, 75% through the section→scene overlap window, then
selects the one with largest JPEG file size (most visual content — blank boards compress
smaller). This prevents capturing blank/transition frames in whiteboard lectures where
content builds incrementally. Pads transcript excerpt 15s backward, writes self-contained
`segments.json`.

`segments.json` carries all data needed by downstream phases — each segment includes:
`segment_id`, full `section` fields, matched `scene`, `keyframe`, `has_visual`,
`global_tags`, `references_mentioned`, and `transcript_excerpt`.
**No separate file join needed at Phase 7.**

**Frame naming:** always variant suffix — `frame_NNNa.jpg` on first use of a scene,
`frame_NNNb.jpg`, `frame_NNNc.jpg` for subsequent sections. Phase 2 scene-midpoint
keyframes (`frame_NNN.jpg`) are never overwritten.

**Misalignments:**
- Speaker introduces topic before slide → excerpt padded 15s backward
- Slide changes mid-sentence → padded 5s forward
- No visual (talking head) → `"has_visual": false`, frame at midpoint as best-effort
- Blank frame detected (JPEG < 50KB) → keyframe discarded, `has_visual: false`

---

## Phase 4.5: Per-Section Video Clip Extraction

```bash
python3 ~/.config/opencode/scripts/lecture-clips.py segments.json video.mp4 -o clips/
```

Extracts per-section video clips for Phase 5 scouting. For each segment:

1. Read `start_seconds` and `end_seconds` from `segments.json`
2. Stream-copy clip via ffmpeg (instant, lossless)
3. If clip exceeds 15MB: re-encode at 640px, 0.5 FPS, mono audio
4. If still exceeds 15MB: second-pass at 480px, 0.3 FPS, CRF 32
5. Write `clip_path` and `clip_status` to `segments.json`

**Output:** `clips/section_NN.mp4` + updated `segments.json`.

**Clip status fields** written to each segment:
- `clip_path`: path to clip (or `null` if extraction failed/skipped)
- `clip_status`: `"ok"` | `"re_encoded"` | `"oversize"` | `"error"` | `"no_visual"`

Phase 5 reads `clip_status` per segment:
- `"ok"` or `"re_encoded"` → send video clip to observer
- `"oversize"`, `"error"`, or `"no_visual"` → fall back to keyframe-only analysis

**Stream-copy note:** ffmpeg `-c copy` seeks to the nearest keyframe before `start_seconds`.
Clips may start up to GOP-size seconds early (typically 2-10s). The 15s backward transcript
padding from Phase 4 already covers this drift — no correctness impact.

---

## Phase 5: Per-Segment AI Scouting (Video-Enhanced)

**Delegate to @observer. Send all sections in PARALLEL calls.** Each section has its own
video clip — no dedup needed (every section has unique time ranges).

For segments where `clip_status` is `"oversize"`, `"error"`, or `"no_visual"`:
fall back to sending the keyframe JPEG + transcript excerpt instead of video.

> You are analyzing a recorded lecture. Each segment has a video clip +
> transcript excerpt spanning [START_TIME] to [END_TIME] in the original
> lecture. The video clip is a sub-extract — use transcript timestamps as
> reference. **All time fields (speaker_emphasis.time, slide_content timing
> hints) must use original lecture time, not clip-internal 00:00.**
>
> For each segment:
>
> 1. `slide_content`: What is VISIBLE in the clip. Describe progression —
>    handwriting appearing on whiteboard, code shown on screen, content
>    building up across frames. Include ~MM:SS timing hints for key transitions
>    (board cleared, formula completed, graph drawn) — approximate within ±5s,
>    useful for sub-section navigation. **ANTI-HALLUCINATION:** describe ONLY
>    what you see in the frames, never invent from transcript.
>
> 2. `content_type`: text_slide | formula_slide | diagram_slide | code_slide |
>    mixed_slide | whiteboard | talking_head | screencast | title_slide | blank
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
> 6. `connections`: How this section connects to the broader lecture structure.
>    Continuation / builds on previous / introduces new concept / complete shift?
>
> 7. `video_note`: Hints for the note composer. Did the video clip capture the
>    full section? Any quick transitions the low FPS might have missed? Is the
>    audio clear enough? Any completeness concerns? (For keyframe-fallback
>    segments, use `image_note` instead — same content.)
>
> Return a JSON object:
> ```json
> {
>   "video": "...",
>   "total_segments": N,
>   "segments": [
>     { "segment_id": 1, "keyframe": "...", "has_visual": true, ... },
>     ...
>   ]
> }
> ```
> Each segment object must include `segment_id`, `keyframe`, and `has_visual` —
> copy these verbatim from the input. Add your analysis fields alongside them.

**Output:** `segments_analyzed.json`. Validate: every video segment has `speaker_added`
AND `speaker_emphasis` (≥1 per segment). Keyframe-fallback segments require `speaker_added`
only. Output wrapped in an object matching `segments.json` structure.

---

## Phase 6: Selective Deep OCR

**Delegate to @observer. Send ALL `needs_ocr` slides in PARALLEL calls.**

> Read the image at `keyframes/frame_XX.jpg`. Extract ALL text and formulas.
> Formulas: LaTeX (block $$...$$, inline $...$). Tables: markdown. Diagrams: describe.
>
> Analyze ONLY this one image. Do NOT include cross-frame comparisons.
>
> The speaker emphasized these parts in this section:
> [SPEAKER_EMPHASIS from Phase 5 — e.g. "Pay attention to boundary conditions" (14:20)]
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

When whiteboard archetype has variant frames (≥2 OCR results from same scene):

1. Group OCR results by base scene number.
2. Compare `## Formulas (LaTeX)` sections within each group.
3. If formula content differs between frames, write `ocr_results/_cross_frame.md`.
   Flag as `correction` (same concept, changed expression) or `addition` (new formula
   absent from earlier frames). One section per comparison pair.
4. Skip if only one OCR frame per scene.

Phase 7 reads `_cross_frame.md` alongside individual OCR results — uses it to add
`> [!important] Correction` callouts where formulas were later corrected.

---

## Phase 7: Note Composition

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

| Callout | When | | Callout | When |
|---------|------|-|---------|------|
| `note` | Speaker's explanation | | `important` | Speaker emphasis (tone, repetition, "this is key") |
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
| 4 | Orchestrator | Runs lecture-fusion.py |
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
