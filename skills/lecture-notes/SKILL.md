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
Phase 1: Assessment      → Orchestrator
Phase 2: Transcription   → transcribe
Phase 3: Scene Detection → lecture-scenes.py
Phase 4: Semantic Seg.   → @oracle
Phase 5: Segment Prep.    → lecture-fusion.py + lecture-clips.py
Phase 6: AI Scouting     → @observer (video+keyframe)
Phase 7: Selective OCR   → @observer (parallel)
Phase 8: Composition     → Orchestrator + @fixer
Phase 9: Review          → @oracle
```

Transcription is local (whisper.cpp, GPU).

---

## Quality Gates (Must Pass Before Proceeding)

| Phase | Gate |
|-------|------|
| **1** | Archetype identified. Output directory + language confirmed with user. |
| **2** | Transcript coherent (head/tail 40 lines). SRT in source video's directory — verify: `ls "${video_abs%.*}.srt"`. |
| **3** | n_min–n_max scenes (n_min = max(12, int(dur/300)), n_max = max(60, int(dur/180))). max_duration < total/2, median < total/8. `scenes.json` valid. All keyframes exist. |
| **4** | 5-15 sections. No time gaps >2s. Every section has ≥1 key_quote. |
| **5** | Every section matched to scene (or `has_visual: false`). Misalignments resolved. Every visual section has a `ok` or `re_encoded` clip. No clip exceeds 15MB. All `clip_status: "ok"` clips playable. |
| **6** | Every segment has `speaker_added` AND `speaker_emphasis` (≥1 per video segment). `slide_content` describes progression. Every segment has `image_note` (keyframe always available). `video_note` non-empty when video is available; `null` if video absent. `needs_ocr` flags set for text/formula slides. |
| **7** | Every `needs_ocr` slide has complete, verified OCR. LaTeX syntax validated. `speaker_emphasis` context used to prioritize OCR accuracy. |
| **8** | All sections present. All images exist. All LaTeX valid. Frontmatter complete. `> [!important]` callouts present for emphasized sections (titles in lecture language). |
| **9** | AI review: zero critical, zero major issues. Video hallucination check: 2-3 segments cross-checked — no fabricated transitions between frames. |

If phase fails gate 3 times: flag for human review, continue best-effort with incomplete sections marked.

---

## Phase 1: Assessment

```bash
ffprobe -v error -show_entries format=duration,format_name,size -of json video.mp4

# 6 frames at evenly spaced intervals across full duration
dur_s=$(ffprobe -v error -show_entries format=duration -of csv=p=0 video.mp4 | cut -d. -f1)
for i in 1 2 3 4 5 6; do
    ffmpeg -ss $((dur_s * (2*i - 1) / 12)) -i video.mp4 \
        -frames:v 1 -q:v 3 /tmp/sample_$(printf '%02d' $i).jpg
done
```

**Delegate to @observer** with the 6 frames:

> Classify these frames: slides / whiteboard / screencast / talking-head / mixed.
> Screencast = code editor, terminal, or IDE (speaker inset is standard, not mixed).
> Which archetype dominates? Speaker visible? Handwriting/drawing present?
> Language of visible text? Text-heavy (OCR needed) or visual (description needed)?
> List 10-20 domain-specific technical terms visible in any frame text.
> Output as comma-separated, max ~150 characters. These prime the transcription model.

**Archetype → pipeline parameters:**

| Archetype | Scene threshold | --min-duration | Special |
|-----------|:---:|:---:|---|
| Slide-heavy | 0.25 | 8s | Standard, catches cursor flickers |
| Whiteboard | 0.05 | 4s | Continuous frames, no scene boundaries |
| Screencast | 0.10 | 4s | Code blocks, syntax preservation |
| Talking head | Skip Phase 3 | — | Transcript-driven, no visuals |
| Mixed | 0.25 | 6s | Per-segment classification handles it |

Thresholds are tuned per archetype to maximize keyframe quality, not scene count.
Scenes are visual bookmarks — `lecture-fusion.py` picks one per section from
candidates. Lower thresholds over-segment into near-identical frames; the extra
candidates are discarded. Worse, exceeding n_max triggers periodic fallback
(uniform time-slicing) — lower quality than content-aware boundaries.

**If not already specified:** Ask user for output directory and language.

**Capture domain terms** from the @observer response. Format as a whisper `--prompt`
string in the lecture's language: a brief context prefix then the domain terms,
comma-separated. Max 30 words (~50 tokens); whisper silently truncates prompts
exceeding `n_text_ctx/2` tokens (224 for large-v3, may be larger for turbo — 50
tokens is safe regardless). If no terms found (talking-head, no visible text),
leave empty.

Evidence: prompt primes decoder vocabulary. Brief context prefix + comma-separated
terms (OpenAI Whisper Prompting Guide). Format example: "Lecture on calculus. theorem,
lemma, proof, derivative, integral" — note the language matches the spoken audio.
If transcribing Serbian, the prompt must be in Serbian: "Predavanje iz matematike.
teorema, lema, dokaz, izvod, integral". Always match the `--language` flag. If
visible slide text is in a different language than the audio, translate the terms
to match `--language` — cross-language prompts provide no priming benefit.

```bash
# Format after @observer returns terms:
# The prompt MUST be in the lecture's language (= --language flag).
WHISPER_PROMPT="[context prefix in lecture language]. [term1], [term2], ..."
# If no terms: WHISPER_PROMPT="" (prompt skipped)
```
# WHISPER_PROMPT carries forward to Phase 2.

---

## Phase 2: Transcription

```bash
# ALWAYS use absolute paths. --output-dir is REQUIRED — SRT must land
# alongside the source video, not in the working directory.
video_abs="$(realpath video.mp4)"
prompt_args=()
[[ -n "$WHISPER_PROMPT" ]] && prompt_args=(--prompt "$WHISPER_PROMPT")

~/.config/opencode/scripts/transcribe "$video_abs" --language LANG \
  --output-dir "$(dirname "$video_abs")" \
  "${prompt_args[@]}"
# Verify SRT exists alongside source video:
srt="${video_abs%.*}.srt"
head -40 "$srt" && tail -40 "$srt"
```

Always use explicit `--language` for non-English. GPU (Vulkan): ~8x realtime.
Media Extended auto-detects sibling SRT files.

---

## Phase 3: Visual Segmentation

```bash
python3 ~/.config/opencode/scripts/lecture-scenes.py video.mp4 -t THRESHOLD --min-duration VALUE -o scenes.json
# → scenes.json + keyframes/frame_XX.jpg
```

Uses threshold from Phase 1.

Gate: n_min–n_max scenes, where n_min = max(12, int(duration_s/300)) and
n_max = max(60, int(duration_s/180)). max scene
duration < total/2, median < total/8. Failed gate → auto-retune (step 0.05, max 3
retries) or periodic fallback with warning.

**Whiteboard lectures will typically FAIL the max_duration gate.** One scene
dominates (59+ min) because gradual chalk/pen writing produces no detectable scene
changes. This is expected — do NOT retry endlessly. The script triggers periodic
fallback automatically (5-minute intervals, minimum 12 scenes). Each periodic
frame captures a different snapshot of board progression. Phase 4 semantic
segmentation supplies the real structure from the transcript.

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
# Use absolute video path for consistent resolution from output directory:
video_abs="$(realpath video.mp4)"
srt="${video_abs%.*}.srt"

python3 ~/.config/opencode/scripts/lecture-fusion.py \
  sections.json scenes.json "$srt" -o segments.json
```

The script: for each section, finds the best-matching scene by overlap. Extracts the
best keyframe (largest JPEG — most visual content, avoids blank frames). Pads transcript
excerpt 15s backward + 5s forward (when a scene match exists; no padding for non-visual segments).
Writes self-contained `segments.json`.

`segments.json` carries all data needed by downstream phases — each segment includes:
`segment_id`, full `section` fields, matched `scene`, `keyframe`, `has_visual`,
and `transcript_excerpt`. Top-level fields: `video`, `duration_seconds`,
`total_segments`, `lecture`, and `global_tags`.
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
video_abs="$(realpath video.mp4)"
python3 ~/.config/opencode/scripts/lecture-clips.py segments.json "$video_abs" --output-dir clips/
```

Extracts per-section video clips for Phase 6 scouting. Run from output directory.

1. Read `start_seconds` and `end_seconds` from `segments.json`
2. Stream-copy clip via ffmpeg (instant, lossless)
3. If clip exceeds 15MB: re-encode — up to 720p, 0.75 FPS, 48kbps mono
4. If still exceeds 15MB: up to 640p, 0.5 FPS, 48kbps mono
5. If still exceeds 15MB: emergency — up to 480p, 0.3 FPS, 48kbps mono (audio preserved)
6. Write `clip_path` and `clip_status` to `segments.json`

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
keyframe JPEG + video clip (no dedup needed — every section has unique time ranges).

If `clip_status` is `oversize` or `error`: video is missing. This should not happen — Phase 5 gate ensures every visual section has a clip. For `no_visual` (talking-head): legitimate skip. In these rare cases: keyframe-only emergency fallback.

**Per-segment observer prompt construction:** For each segment, build the prompt by:
1. Always send the keyframe JPEG via Read tool — use the `keyframe` path from `segments.json` (canonical source). Do NOT use `segments_analyzed.json` (orchestrator-constructed, may have stale paths).
2. Send the video clip via \`python3 ~/.config/opencode/scripts/analyze-video.py <clip> "<PROMPT>"\` (temporal progression + audio for speaker_emphasis). Keyframe + video are complementary — keyframe catches full-res detail low-FPS video may miss; video captures movement and audio the still can't convey.
3. If \`clip_status\` is \`no_visual\` (talking-head segment): keyframe-only — legitimate design path. Audio-derived fields (`speaker_added`, `speaker_emphasis`) are not expected.
4. If \`clip_status\` is \`oversize\` or \`error\`: keyframe-only emergency fallback. This should not happen — Phase 5 gate ensures every visual section has a clip.
5. Injecting \`[START_TIME]\` and \`[END_TIME]\` — use \`start_time\` and \`end_time\` (HH:MM:SS format) from the segment's \`section\` fields
6. Including the `transcript_excerpt` from `segments.json`
7. Optionally including the section title for context

Template:

> You are analyzing a recorded lecture segment. You receive:
> - A high-res keyframe JPEG (always) — best still for precise visual detail
> - A video clip — temporal progression + audio for speaker_emphasis
> - Transcript excerpt spanning [START_TIME] to [END_TIME] in the original lecture
>
> Use the keyframe for equations, annotations, diagrams — the video may be
> low-FPS and miss fine detail. Use the video for temporal progression and
> audio cues (speaker_emphasis). All time fields must use original lecture
> time, not clip-internal 00:00.
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
> 7. `video_note` — audio quality, transitions, temporal completeness
>    (required, non-empty string when video is available; `null` if video absent).

> 8. `image_note` — keyframe resolution, angle, partial visibility
>    (required, non-empty string; keyframe is always available).
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
>   "video_note": "...",
>   "image_note": "..."
> }
> ```
> Copy `segment_id`, `keyframe`, and `has_visual` verbatim from the prompt.
> Add your analysis fields alongside them.


**Output:** `segments_analyzed.json`. Orchestrator wraps single-segment observer outputs:
```json
{ "video": "video.mp4", "total_segments": N, "segments": [...] }
```
Validate: every video segment (ok/re_encoded) requires `speaker_added` (non-empty string), `speaker_emphasis` (≥1 entry), `video_note` (non-empty string), and `image_note` (non-empty string). Segments with missing video require `speaker_added` + `image_note` (both non-empty); `video_note` must be `null`.
**Exception (no-audio):** `speaker_added: ""` and `speaker_emphasis: []` are valid — skip those callouts.

**→ GATE: Check `needs_ocr` in segments_analyzed.json. If ANY segment has `needs_ocr: true`, Phase 7 IS REQUIRED for those segments. Do not skip.**

---

## Phase 7: Selective Deep OCR

**Delegate to @observer. Send ALL `needs_ocr` slides in PARALLEL calls.**

**Keyframe source:** Use `keyframe` paths from `segments.json` (canonical, produced by fusion.py). Do NOT use `segments_analyzed.json` — it is orchestrator-constructed and may contain stale paths from manual copy-paste errors.

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

**Save each as `ocr_results/frame_XX.txt`** (relative to the output directory set in Phase 1). Use these exact section headers —
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

**Empty result handling:** Some @observer OCR calls return empty results (~30%
observed rate with parallel dispatch). After collecting OCR outputs, check each
`ocr_results/frame_XX.txt` file: if it's empty, contains only `<task_result></task_result>`,
or has section headers with no content, retry that single frame's OCR call once.
Retries consistently succeed. No data loss — just a re-dispatch.

### Cross-Frame Comparison (whiteboard lectures)

When multiple OCR results exist for the same scene (variant frames frame_NNNa/b/c):
Compare `## Formulas (LaTeX)` sections by content similarity. Write `ocr_results/_cross_frame.md`
with a table: `| Frame | Changed | New content |`. Use for `> [!warning]` correction callouts (title in lecture language).

---

## Phase 8: Note Composition

**Agent:** Orchestrator (integration). @fixer for per-section parallel drafting if 10+ sections.

### File structure

```
OUTPUT_DIR/
└── Lecture Title/
    ├── Lecture Title.md
    ├── clips/             ← per-section video clips
    ├── keyframes/
    ├── slides/            ← selected frames copied from keyframes
    └── ocr_results/
```

**slides/ selection:** Copy each segment's `keyframe` path from `segments.json` into `slides/`, renaming to `slide_NN.jpg`. Every section gets its corresponding visual — no manual selection needed.

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
source_transcript: "video.srt"  # alongside source video (Phase 2 --output-dir)
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

[OCR: Text, Formulas (LaTeX), Diagrams, Tables, Annotations — incorporate all relevant OCR output]

[Write the section's core content here — using slide_content for visual progression and speaker_added for explanations. Plain text carries the narrative.]

> <!-- Use callouts selectively. Callout TITLES (text after [!type]) must be in the
>      lecture's language (match --language flag). [!type] syntax stays English. -->

> [!note] [Speaker's explanation — in lecture language]
> [What the speaker said NOT on the slide — the most valuable part]

> [!warning] [Emphasis/Exam-relevant — in lecture language]
> [When speaker stressed this point]

> [!tip] [Practical example — in lecture language]
> [Concrete example with full context]

> [!important] [Speaker emphasis — in lecture language]
> "Pay attention to boundary conditions" — speaker slows down, repeats (≈14:20)

> [!info] [Connection — in lecture language]
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
4. Underscores only inside \`$...$\` or \`$$...$$\` — raw underscores in prose render as italics
5. End with `## Summary` + `## Links & References`

### Connection Synthesis

After drafting all sections, review `segments_analyzed.json` for `connection_type` values across sections. Write `> [!info]` connection callouts that show how sections build on each other (title in lecture language). The orchestrator has full context — identify narrative arcs, prerequisite chains, and thematic groupings the observer (single-segment) could not see.

### Post-composition checklist

Verify all sections present, all images exist, all LaTeX valid, frontmatter complete,
summary + links present.
- Prose thoroughness: every section has substantive plain text (concepts, derivations, flow), not only callout blocks.
- Multi-video lectures: add `source_video_N` and `source_transcript_N` for each part. Update `duration` to combined total.

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
> Flag segments with unexpectedly missing video (`oversize`/`error`) for human review. `no_visual` segments are intentional — no action needed.
> **Markdown:** Unescaped underscores? Valid wikilinks? `#t=` syntax correct?
> **Completeness:** Summary? Links? Frontmatter?
>
> Report by category. Severity: critical, major, minor, cosmetic.

Apply fixes. Re-run review if critical. **Gate: zero critical, zero major.**

---

## Edge Cases

| Case | Adjustment |
|------|-----------|
| **Whiteboard** | Threshold 0.05. Sequential frames. "Handwritten content" in OCR prompt. |
| **Screencast** | Threshold 0.10. Code blocks with language annotation. Covers coding sessions, video tutorials, terminal demos. |
| **Talking head** | Skip Phase 3, 6, 7. Transcript-driven. Heavier on quotes. No domain prompt. Generate minimal scenes.json for Phase 5 (see Special Workflows below). |
| **Non-English** | Explicit `--language` in Phase 2. OCR prompts specify language + script. |
| **Poor audio** | Re-transcribe with `ffmpeg -af "highpass=f=200,lowpass=f=3000,afftdn"`. Mark sections `> [!warning]` audio quality callout (title in lecture language). |
| **No audio** | Skip Phase 2, 4. Generate minimal inputs for Phase 5 (see Special Workflows below). Phase 6: keyframe-only, relaxed gate (omit `speaker_added` and `speaker_emphasis` — no audio source). Heavier reliance on OCR. |
| **Animations** | Threshold 0.40 to avoid false boundaries. Use most complete frame. |
| **Multi-video** | Process parts independently through Phase 7. Merge in Phase 8. `[[part1.mp4#t=...]]` per source. |

### Special workflows

When a phase is legitimately skipped (no visuals, no audio), the downstream phases
still need compatible input files. Generate minimal placeholders — never skip a phase
that leaves a required input missing. The goal is to preserve ALL available information
in every phase's output.

**Talking head (no visuals — Phase 3, 6, 7 skipped):**
Phase 5 needs `scenes.json`. Generate a minimal one so fusion.py preserves Phase 4's
semantic structure in `segments.json`:

```bash
# Empty scenes list: best_scene() returns None → has_visual: false per section
# Use real video path so ffmpeg has valid input (frames extracted but discarded)
echo "{\"video\":\"$video_abs\",\"duration_seconds\":0,\"scenes\":[]}" > scenes.json
```

All sections from Phase 4 carry through to Phase 8 via `segments.json` with
`has_visual: false`. No visual data lost — there was none.

**Phase 8 composition (Phases 6-7 skipped):** Compose from `segments.json`
directly — `segments_analyzed.json` is not created. Use Phase 4 fields:
`key_quotes` → `> [!important]` callouts, `concepts_introduced` → section narrative,
`transcript_excerpt` (Phase 5) → body text. Skip image embeds and
`speaker_added`/`speaker_emphasis` callouts. Derive cross-section connections
from Phase 4's sequential section ordering — no `connection_type` available.

**No audio (Phase 2, 4 skipped):**
Phase 5 needs `sections.json` and `transcript.srt`. Generate minimal inputs to
preserve Phase 3's visual keyframe data in `segments.json`:

Create `sections.json` with a single global section (substitute actual `DUR`
from Phase 1 ffprobe):
```json
{"lecture": {"title": "Silent Video", "speaker": "", "language": "xx"},
 "sections": [{"section_id": 1, "title": "Full Video",
   "start_seconds": 0, "end_seconds": DUR,
   "summary": "Visual content only",
   "concepts_introduced": [], "key_quotes": [], "content_type": "mixed"}]}
```
Then create an empty SRT stub **alongside the source video** (Phase 5 resolves SRT path via `$(dirname "$video_abs")/...`):
```bash
touch "${video_abs%.*}.srt"
```

Phase 5 produces one segment with `has_visual: true` and keyframe from the
longest Phase 3 scene. Phase 6 runs keyframe-only. All visual info preserved.

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
3. **Phase 6 is parallel:** Send all per-segment keyframes + video clips to @observer simultaneously. Each segment has its own keyframe and video clip — calls are independent with no shared state.
4. **Phase 7 is parallel:** Send all `needs_ocr` slides to @observer simultaneously. Independent images, no cross-contamination risk.
5. **Quality over speed.** Each phase exists to capture information the next phase depends on. Skipping a phase produces incomplete notes — run all 9 phases regardless of time.
6. **Gate failures → retry or best-effort.** If a phase fails its quality gate 3 times, continue with incomplete sections marked for human review. Never block the pipeline.
7. **Verify outputs before proceeding.** Check file existence, line counts, JSON validity at each phase boundary.
8. **Script errors → fix, don't skip.** If a local script fails (transcribe, lecture-scenes.py, lecture-clips.py), resolve the error first. These are deterministic — failures are fixable, not random.

**Skill dependencies:** Orchestrator: `audio-analysis` (transcribe details). @observer (phases 6-7): `video-analysis` (model options), `lecture-notes` (output field spec).

### Obsidian integration

- **Check:** If output dir is in an Obsidian vault → verify Media Extended plugin.
  If missing: warn user. Timestamps will be plain links. All else (callouts, LaTeX,
  wikilinks, embeds) work with core Obsidian.
- **SRT subtitles:** `transcript.srt` alongside source video file (Phase 2 `--output-dir`) → Media Extended
  auto-detects and shows interactive subtitles during playback.
