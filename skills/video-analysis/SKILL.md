---
name: video-analysis
description: Analyze video files using Kimi K2.6 native video_url support. Use when the user asks to analyze a video, describe video content, extract information from video, or understand what happens in a video file.
---

# Video Analysis Skill

## When to Use

- User asks to analyze a video file (mp4, mov, avi, webm, etc.)
- User wants a description of what happens in a video
- User needs text/video content extracted from a recording
- Video is at a known file path

## How to Analyze Video

Use the `kimi-video.py` script, which sends the video directly to Kimi K2.6's native video analysis:

```bash
python3 ~/.config/opencode/scripts/kimi-video.py <video_path> [prompt]
```

The script:
- Reads the video file from disk
- Base64-encodes it and sends it as `video_url` content to Kimi K2.6 API
- Kimi K2.6 processes the video natively (keyframe extraction)
- Returns a plain-text analysis

**Limitations:**
- Max video size: 100MB (inline base64 limit)
- Supported formats: mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp
- No audio analysis — video is visual-only (keyframes). For audio, extract with ffmpeg first.

## Environment

The script requires `KIMI_API_KEY` environment variable — already set in the session.
It uses the `openai` Python package (already installed via `uv pip`).

## Examples

```
# Basic analysis
python3 ~/.config/opencode/scripts/kimi-video.py /tmp/demo.mp4

# Specific question
python3 ~/.config/opencode/scripts/kimi-video.py /tmp/demo.mp4 "What UI elements appear after clicking the button?"

# Compare two videos
python3 ~/.config/opencode/scripts/kimi-video.py /tmp/before.mp4 "Describe the layout"
python3 ~/.config/opencode/scripts/kimi-video.py /tmp/after.mp4 "Describe the layout"
```
