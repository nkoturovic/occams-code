#!/usr/bin/env python3
"""Analyze a video file using OpenRouter → Gemini.

Gemini processes both audio and visual streams from video (1fps sampling +
1Kbps audio). Default model: ~google/gemini-pro-latest (auto-upgrades to
latest Gemini Pro — currently 3.1 Pro Preview). ≤20MB inline.

Usage:
  analyze-video.py <video_path> [prompt]
  analyze-video.py -m google/gemini-3.1-pro-preview <video_path> [prompt]

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
# Config
# ---------------------------------------------------------------------------

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "~google/gemini-pro-latest"
MAX_INLINE_MB = 20
ENV_KEY = "OPENROUTER_API_KEY"

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

def analyze(model: str, video_path: Path, prompt: str) -> str:
    api_key = os.environ.get(ENV_KEY)
    if not api_key:
        sys.exit(f"Error: {ENV_KEY} environment variable not set")

    file_size = video_path.stat().st_size
    max_bytes = MAX_INLINE_MB * 1024 * 1024
    if file_size > max_bytes:
        mb = file_size / 1024 / 1024
        sys.exit(
            f"Error: video too large ({mb:.1f} MB). "
            f"OpenRouter inline limit is {MAX_INLINE_MB} MB. "
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
        "HTTP-Referer": "https://github.com/nkoturovic/occams-code",
        "X-Title": "occams-code video analysis",
    }

    req = urllib.request.Request(ENDPOINT, data=body, headers=headers)

    print(
        f"Analyzing: {video_path.name} ({file_size / 1024 / 1024:.1f} MB) "
        f"with {model} (audio+visual)...",
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
        description="Analyze video using OpenRouter → Gemini (audio+visual)",
    )
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_MODEL,
        help=f"Model ID (default: {DEFAULT_MODEL})",
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

    try:
        response = analyze(args.model, video_path, args.prompt)
        print(response)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"API error ({e.code}): {body[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


if __name__ == "__main__":
    main()
