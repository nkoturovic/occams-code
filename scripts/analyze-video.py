#!/usr/bin/env python3
"""Analyze a video file using a multimodal LLM that supports native video input.

Supported providers:
  kimi       Kimi K2.6 (KIMI_API_KEY) — visual keyframes, no audio track
  openrouter OpenRouter (OPENROUTER_API_KEY) — proxies to Gemini etc,
             which process both audio AND visual streams

Usage:
  analyze-video.py <video_path> [prompt]
  analyze-video.py --provider openrouter <video_path> [prompt]
  analyze-video.py --provider openrouter --model google/gemini-2.5-pro <video_path> [prompt]

Zero dependencies — stdlib only. No openai SDK, no requests.
"""

import argparse
import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------

PROVIDERS = {
    "kimi": {
        "env_key": "KIMI_API_KEY",
        "endpoint": "https://api.moonshot.cn/v1/chat/completions",
        "model": "kimi-k2.6",
        "max_inline_mb": 100,
        "audio_track": False,
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        "model": "google/gemini-3-flash-preview",
        "max_inline_mb": 20,   # OpenRouter recommends <20MB for inline
        "audio_track": True,   # Gemini processes both audio+visual from video
    },
}

MIME_MAP = {
    ".mp4":  "mp4",
    ".mpeg": "mpeg",
    ".mov":  "mov",
    ".avi":  "avi",
    ".flv":  "x-flv",
    ".mpg":  "mpg",
    ".webm": "webm",
    ".wmv":  "wmv",
    ".3gpp": "3gpp",
    ".3gp":  "3gpp",
}


def detect_media_type(path: Path) -> str:
    return MIME_MAP.get(path.suffix.lower(), "mp4")


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def analyze(provider: str, model: str, video_path: Path, prompt: str) -> str:
    cfg = PROVIDERS[provider]
    api_key = os.environ.get(cfg["env_key"])
    if not api_key:
        sys.exit(f"Error: {cfg['env_key']} environment variable not set")

    file_size = video_path.stat().st_size
    max_bytes = cfg["max_inline_mb"] * 1024 * 1024
    if file_size > max_bytes:
        mb = file_size / 1024 / 1024
        sys.exit(
            f"Error: video too large ({mb:.1f} MB). "
            f"{provider} inline limit is {cfg['max_inline_mb']} MB. "
            "Trim or compress the video first."
        )

    media_type = detect_media_type(video_path)
    with video_path.open("rb") as f:
        video_b64 = base64.b64encode(f.read()).decode("utf-8")

    body = json.dumps({
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "video_url",
                    "video_url": {
                        "url": f"data:video/{media_type};base64,{video_b64}",
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    }).encode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://github.com/nkoturovic/occams-code"
        headers["X-Title"] = "occams-code video analysis"

    req = urllib.request.Request(cfg["endpoint"], data=body, headers=headers)

    print(
        f"Analyzing: {video_path.name} ({file_size / 1024 / 1024:.1f} MB) "
        f"with {model}{' (audio+visual)' if cfg['audio_track'] else ' (visual only)'}...",
        file=sys.stderr,
    )

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    return result["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze video using a multimodal LLM",
    )
    parser.add_argument(
        "-p", "--provider",
        choices=list(PROVIDERS),
        default="kimi",
        help="Provider to use (default: kimi)",
    )
    parser.add_argument(
        "-m", "--model",
        default=None,
        help="Model ID override (provider-specific)",
    )
    parser.add_argument(
        "video",
        help="Path to video file",
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="Describe this video in detail.",
        help="Prompt for analysis (default: describe in detail)",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        sys.exit(f"Error: file not found: {args.video}")

    provider = args.provider
    model = args.model or PROVIDERS[provider]["model"]

    try:
        response = analyze(provider, model, video_path, args.prompt)
        print(response)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"API error ({e.code}): {body[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


if __name__ == "__main__":
    main()
