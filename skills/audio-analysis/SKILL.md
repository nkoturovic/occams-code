---
name: audio-analysis
description: Transcribe speech to text from audio or video files — generate subtitles, extract lecture notes, convert podcasts or meetings to text. Use when the user has an audio/video file and wants a transcript, subtitles, or text version of spoken content, even if they don't say "transcribe." Do not use for visual video analysis — that requires video-analysis instead.
compatibility: Requires nix and ffmpeg. Model auto-downloaded on first use.
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
transcribe /path/to/audio.mp3

# Video — auto-extracts audio first, SRT named after original file in CWD
transcribe /path/to/lecture.mp4

# Specific language (SRT output: ./lecture.srt)
transcribe /path/to/lecture.mp4 --language sr

# Plain text output (no timestamps), custom name
transcribe /path/to/audio.mp3 -otxt -of my-notes

# Custom output path
transcribe /path/to/audio.mp3 -of /home/user/transcript
```

**Default output behavior:** SRT file is written to the current working directory using the original filename (e.g. `lecture.mp4` → `./lecture.srt`). The `-of` flag (or `--output-file`) overrides this if passed explicitly. Additional whisper.cpp flags (e.g. `-otxt`, `-lrc`, `--language`, `--max-len`) are forwarded as-is.

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
- Vulkan GPU (AMD Radeon 860M, RADV): **~8x realtime** (64 min audio → ~8 min) — confirmed working via `VK_ICD_FILENAMES` and `LD_LIBRARY_PATH` env vars in the script

## Formats Supported

- Audio: wav, mp3, flac, ogg, aac, m4a, opus
- Video: mp4, mkv, webm, mov, avi (auto-extracted to audio)

## Environment

- `nix` (builds whisper.cpp)
- `ffmpeg` (audio extraction from video)
- Model auto-downloaded on first use
