#!/usr/bin/env python3
"""Scene detection and keyframe extraction for lecture videos.

Detects scene boundaries using ffmpeg's select filter, extracts one keyframe
per scene at midpoint, and outputs scenes.json manifest.

Usage:
  lecture-scenes.py <video_path> [-t THRESHOLD] [-o OUTPUT_DIR]

Threshold:
  0.30  Slide-heavy presentations (default) — slide transitions are large changes
  0.15  Whiteboard/chalkboard — gradual drawing changes
  0.10  Screencast/code — subtle UI changes (more false positives)
  >0.40 Animations with incremental builds — avoids false boundaries

Output: scenes.json + keyframes/ directory with frame_XX.jpg files.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLD = 0.30
MIN_SCENES = 5
MAX_SCENES = 40
FALLBACK_INTERVAL = 10  # seconds, when scene detection produces too few scenes


def panic(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def run_ffprobe(video_path: str) -> dict:
    """Extract video metadata: duration, format, size."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration,format_name,size",
        "-of", "json", video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        panic(f"ffprobe failed: {result.stderr.strip()}")
    fmt = json.loads(result.stdout).get("format", {})
    return {
        "duration": float(fmt.get("duration", 0)),
        "format": fmt.get("format_name", "unknown"),
        "size_bytes": int(fmt.get("size", 0)),
    }


def detect_scenes(video_path: str, threshold: float) -> list[float]:
    """Run ffmpeg scene detection and return list of scene-start timestamps
    (in seconds), including 0.0 for the start."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # showinfo writes to stderr
    output = result.stderr

    timestamps = []
    # showinfo lines look like:
    # [Parsed_showinfo_0 @ 0x...] n:105 pts:105 pts_time:4.2 ...
    for line in output.split("\n"):
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            timestamps.append(float(m.group(1)))

    # Ensure start is at 0.0
    if not timestamps or timestamps[0] > 1.0:
        timestamps.insert(0, 0.0)

    # Remove very close duplicates (within 0.5s)
    deduped = [timestamps[0]]
    for t in timestamps[1:]:
        if t - deduped[-1] > 0.5:
            deduped.append(t)

    return deduped


def extract_keyframe(video_path: str, time_s: float, output_path: str) -> None:
    """Extract a single frame at the given time."""
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", str(time_s), "-i", video_path,
        "-frames:v", "1", "-q:v", "2", output_path,
    ]
    subprocess.run(cmd, check=True)


def build_scenes(timestamps: list[float], duration: float) -> list[dict]:
    """Convert timestamp list into structured scenes list."""
    scenes = []
    for i, ts in enumerate(timestamps):
        end_ts = timestamps[i + 1] if i + 1 < len(timestamps) else duration
        midpoint = (ts + end_ts) / 2
        scenes.append({
            "scene_id": i + 1,
            "start_seconds": round(ts, 2),
            "end_seconds": round(end_ts, 2),
            "midpoint_seconds": round(midpoint, 2),
        })
    return scenes


def fmt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scene detection and keyframe extraction for lecture videos"
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Scene change threshold (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "-o", "--output",
        default=".",
        help="Output directory (default: current directory)",
    )
    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        panic(f"file not found: {args.video}")

    out_dir = Path(args.output).resolve()
    keyframes_dir = out_dir / "keyframes"
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    # ── Get metadata ──
    meta = run_ffprobe(str(video_path))
    duration = meta["duration"]
    print(f"Video: {video_path.name} ({duration/60:.1f} min, "
          f"{meta['size_bytes']/1024/1024:.0f} MB)", file=sys.stderr)

    # ── Scene detection ──
    timestamps = detect_scenes(str(video_path), args.threshold)
    print(f"Scene detection (threshold={args.threshold}): "
          f"{len(timestamps)} boundaries", file=sys.stderr)

    # ── Fallback if too few scenes ──
    scenes = build_scenes(timestamps, duration)
    if len(scenes) < MIN_SCENES:
        print(f"Too few scenes ({len(scenes)}). "
              f"Falling back to periodic sampling (every {FALLBACK_INTERVAL}s).",
              file=sys.stderr)
        n = int(duration / FALLBACK_INTERVAL)
        timestamps = [i * FALLBACK_INTERVAL for i in range(n)]
        scenes = build_scenes(timestamps, duration)

    # ── Cap if too many ──
    if len(scenes) > MAX_SCENES:
        print(f"Too many scenes ({len(scenes)}), capping to {MAX_SCENES}",
              file=sys.stderr)
        step = duration / MAX_SCENES
        timestamps = [i * step for i in range(MAX_SCENES)]
        scenes = build_scenes(timestamps, duration)

    # ── Extract keyframes ──
    print(f"Extracting {len(scenes)} keyframes...", file=sys.stderr)
    for scene in scenes:
        sid = scene["scene_id"]
        fname = f"frame_{sid:02d}.jpg"
        fpath = keyframes_dir / fname
        extract_keyframe(str(video_path), scene["midpoint_seconds"], str(fpath))
        scene["keyframe"] = str(fpath)
        scene["start_time"] = fmt_time(scene["start_seconds"])
        scene["end_time"] = fmt_time(scene["end_seconds"])

    # ── Write manifest ──
    manifest_path = out_dir / "scenes.json"
    manifest = {
        "video": str(video_path.resolve()),
        "duration_seconds": round(duration, 2),
        "threshold": args.threshold,
        "total_scenes": len(scenes),
        "scenes": scenes,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Done. {len(scenes)} scenes → {manifest_path}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
