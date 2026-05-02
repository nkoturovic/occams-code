#!/usr/bin/env python3
"""Analyze a video file using Kimi K2.6's native video_url support.

Usage:
    kimi-video.py <video_path> [optional prompt]

The Kimi API key is read from the KIMI_API_KEY environment variable.
The video is sent as base64-encoded video_url content — Kimi K2.6
processes it natively (keyframe extraction), not via a separate pipeline.

For large videos (>100MB), use the Kimi Files API (upload first, then
reference via ms:// protocol).
"""

import base64
import os
import sys
from pathlib import Path

from openai import OpenAI


# 100MB body size limit (Kimi recommendation for inline base64)
MAX_INLINE_BYTES = 100 * 1024 * 1024


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <video_path> [prompt]", file=sys.stderr)
        print("", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print(f"  {sys.argv[0]} video.mp4", file=sys.stderr)
        print(f"  {sys.argv[0]} video.mp4 'Describe what happens in this video'", file=sys.stderr)
        sys.exit(1)

    video_path = sys.argv[1]
    prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Describe this video in detail."

    video_file = Path(video_path)
    if not video_file.exists():
        print(f"Error: file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("KIMI_API_KEY")
    if not api_key:
        print("Error: KIMI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    file_size = video_file.stat().st_size
    if file_size > MAX_INLINE_BYTES:
        print(
            f"Error: video too large ({file_size / 1024 / 1024:.1f} MB). "
            f"Max inline is {MAX_INLINE_BYTES / 1024 / 1024:.0f} MB. "
            "Use Kimi Files API for larger videos.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract mime type from extension
    suffix = video_file.suffix.lower().lstrip(".")
    mime_map = {
        "mp4": "mp4",
        "mpeg": "mpeg",
        "mov": "mov",
        "avi": "avi",
        "flv": "x-flv",
        "mpg": "mpg",
        "webm": "webm",
        "wmv": "wmv",
        "3gpp": "3gpp",
        "3gp": "3gpp",
    }
    media_type = mime_map.get(suffix, "mp4")  # default to mp4

    # Encode video
    with video_file.open("rb") as f:
        video_data = f.read()

    video_b64 = base64.b64encode(video_data).decode("utf-8")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.moonshot.cn/v1",
    )

    print(f"Analyzing: {video_file.name} ({file_size / 1024 / 1024:.1f} MB)...", file=sys.stderr)

    response = client.chat.completions.create(
        model="kimi-k2.6",
        messages=[
            {
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
            },
        ],
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main()
