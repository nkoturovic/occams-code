---
name: video-analysis
description: Analyze video files using multimodal LLMs (Kimi K2.6 for visual, Gemini via OpenRouter for audio+visual). Use when the user asks to analyze a video, describe video content, extract information from video, or understand what happens in a video file.
---

# Video Analysis Skill

## When to Use

- User asks to analyze a video file (mp4, mov, avi, webm, etc.)
- User wants a description of what happens in a video
- User needs text/video content extracted from a recording
- User wants video analysis with audio track understanding (lectures, talks, etc.)

## How to Analyze Video

Use the `analyze-video.py` script. Zero dependencies — stdlib only.

```bash
# Default: Kimi K2.6 (visual keyframes, no audio)
python3 ~/.config/opencode/scripts/analyze-video.py /tmp/video.mp4

# With audio track analysis (Gemini via OpenRouter)
python3 ~/.config/opencode/scripts/analyze-video.py --provider openrouter /tmp/video.mp4

# Specific prompt
python3 ~/.config/opencode/scripts/analyze-video.py /tmp/video.mp4 "What happens after 0:30?"

# Specific model
python3 ~/.config/opencode/scripts/analyze-video.py --provider openrouter --model google/gemini-3-pro-preview /tmp/video.mp4
```

## Provider Comparison

| Provider | Flag | Model | Audio? | Limit | Best for |
|---|---|---|---|---|---|
| Kimi K2.6 (default) | `--provider kimi` or omit | `kimi-k2.6` | No | 100MB | UI flows, code recordings, visual-only |
| OpenRouter → Gemini | `--provider openrouter` | `google/gemini-3-flash-preview` | Yes | 20MB | Lectures, talks, audio-dependent content |

## Environment

- `KIMI_API_KEY` (default provider) — already set in the session
- `OPENROUTER_API_KEY` (for `--provider openrouter`) — already set in the session

## Limitations

- Max file sizes: Kimi 100MB, OpenRouter 20MB (inline base64)
- Supported formats: mp4, mpeg, mov, avi, flv, mpg, webm, wmv, 3gpp
- Kimi: visual only (keyframe extraction)
- Gemini (via OpenRouter): audio+visual, 1fps sampling, supports timestamps

## Fallback

For small clips (≤8MB), `zai_vision` MCP `video_analysis` is available but lower quality (server-side pipeline, not model-native).
