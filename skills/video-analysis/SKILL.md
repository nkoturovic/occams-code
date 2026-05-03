---
name: video-analysis
description: Analyze video files — describe visual content, extract text from screen recordings, identify UI elements and timing, summarize lectures. Use when the user has a video file (mp4, mov, webm, etc.) and wants to understand what happens in it, even if they don't explicitly ask for "analysis." Do not use for audio transcription or speech-to-text — that requires audio-analysis instead.
compatibility: Requires OPENROUTER_API_KEY (already set in session).
---

# Video Analysis Skill

## When to Use

- User asks to analyze a video file (mp4, mov, avi, webm, etc.)
- User wants a description of what happens in a video
- User needs text/video content extracted from a recording
- User wants video analysis with audio track understanding (lectures, talks, etc.)

## How to Analyze Video

Use the `analyze-video.py` script. Single provider: **OpenRouter → Gemini**.
Gemini processes both audio and visual streams (1fps sampling + 1Kbps audio).
Zero dependencies — stdlib only.

```bash
# Default: Gemini via OpenRouter (audio+visual, best for lectures/talks)
python3 ~/.config/opencode/scripts/analyze-video.py /tmp/video.mp4

# Specific prompt (Serbian lecture, math content)
python3 ~/.config/opencode/scripts/analyze-video.py /tmp/video.mp4 \
  "Describe all visible content: slide titles, text, math formulas (LaTeX), diagrams. Language: Serbian."

# Specific model
python3 ~/.config/opencode/scripts/analyze-video.py -m google/gemini-3.1-pro-preview /tmp/video.mp4
```

## Model

Default: `~google/gemini-pro-latest` — auto-upgrades to latest Gemini Pro (currently 3.1 Pro Preview). Override with `-m`.

Supported formats: mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp. Max 20MB inline.

## Environment

- `OPENROUTER_API_KEY` — already set in the session

## Limitations

- Max file size: 20MB (inline base64)
- Gemini: audio+visual, 1fps sampling, supports timestamps

## Fallback

For small clips (≤8MB), `zai_vision` MCP `video_analysis` is available but lower quality (server-side pipeline, not model-native).

## Combined Audio+Video Pipeline

### Short clips (≤20MB)

Gemini via OpenRouter handles audio+visual in one call:

```bash
python3 ~/.config/opencode/scripts/analyze-video.py slide_chunk.mp4 \
  "Describe all visible content and what the speaker says. Language: Serbian."
```

### Long lectures (>20MB)

Two-pass approach — minimizes paid API calls:

```bash
# Pass 1: Audio transcription (free, local)
transcribe lecture.mp4 --language sr

# Pass 2: Scout with Gemini on sparse keyframes (one cheap call)
mkdir -p keyframes
ffmpeg -i lecture.mp4 -vf "fps=1/30" -q:v 5 keyframes/frame_%04d.jpg
# → @observer reads every Nth keyframe, reports slide boundaries + topics

# Pass 3: Detailed OCR on slide frames (free, via @observer Read tool)
# @observer reads keyframes at identified boundaries, extracts text + LaTeX math
```
