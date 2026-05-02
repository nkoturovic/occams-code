---
name: audio-analysis
description: Transcribe speech to text from audio/video files using whisper.cpp (local, Vulkan GPU). Use when the user asks to transcribe audio, extract text from a lecture/talk, convert speech to text, or generate subtitles.
---

# Audio Analysis Skill

## When to Use

- User asks to transcribe audio or video
- User wants text from a lecture, podcast, meeting recording
- User needs subtitles (SRT) from a video
- User says "convert this to text", "transcribe this", "speech to text"

## How to Transcribe

Use the `transcribe` script — local whisper.cpp with Vulkan GPU:

```bash
# Basic — auto language detection, SRT output
~/.config/opencode/scripts/transcribe /path/to/audio.mp3

# Video — auto-extracts audio first
~/.config/opencode/scripts/transcribe /path/to/lecture.mp4

# Specific language
~/.config/opencode/scripts/transcribe /path/to/audio.wav --language sr

# Plain text output (no timestamps)
~/.config/opencode/scripts/transcribe /path/to/audio.mp3 -otxt -of /tmp/notes

# Custom output location
~/.config/opencode/scripts/transcribe /path/to/audio.mp3 --output-file /home/user/transcript
```

## What It Does

1. If input is video → `ffmpeg` extracts 16kHz mono WAV audio
2. `whisper-cli` (whisper.cpp, Vulkan GPU) transcribes speech to text
3. By default, outputs SRT file with timestamps (or whatever format the flags request)

## Backend

- **whisper.cpp** (C++, Vulkan GPU on AMD Radeon 860M + Zen 4 AVX-512 CPU)
- Model: `ggml-large-v3-turbo` (1.6 GB, best Serbian accuracy among GGML models)
- Model stored in `~/.local/share/opencode/models/whisper/` (auto-downloaded if missing)
- Built via nix from `github:nkoturovic/kotur-nixpkgs#whisper-cpp-vulkan`

## Performance

- CPU only (Zen 4 AVX-512): ~0.5x realtime (64 min audio → ~32 min)
- Vulkan GPU: ~3-5x realtime (64 min audio → ~6-13 min)
- GPU not yet available in nix sandbox — falls back to CPU automatically

## Formats Supported

- Audio: wav, mp3, flac, ogg, aac, m4a, opus
- Video: mp4, mkv, webm, mov, avi (auto-extracted to audio)

## Environment

- `nix` (builds whisper.cpp)
- `ffmpeg` (audio extraction from video)
- Model auto-downloaded on first use
