#!/usr/bin/env python3
"""Extract per-section video clips from a lecture using ffmpeg.

Reads segments.json (produced by lecture-fusion.py) and extracts one clip per
segment via a 4-pass fallback pipeline (stream-copy → 720p → 640p → 480p).

Usage:
  lecture-clips.py segments.json video.mp4 [--output-dir DIR] [--max-mb MB] [--digits N]
"""

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def panic(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def file_mb(path: Path) -> float:
    return path.stat().st_size / 1024 / 1024


def run_ffmpeg(cmd: list[str]) -> tuple[bool, str]:
    """Run ffmpeg, return (success, stderr)."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0, result.stderr


def extract_clip(
    video: Path,
    start: float,
    end: float,
    out: Path,
    max_mb: int,
) -> tuple[str, Path | None]:
    """4-pass extraction. Returns (status, clip_path)."""

    # Pass 1: stream-copy
    cmd1 = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video),
        "-c", "copy",
        str(out),
    ]
    ok, _ = run_ffmpeg(cmd1)
    if ok and out.exists() and file_mb(out) <= max_mb:
        return "ok", out

    if not ok:
        # Stream-copy failed (e.g. incompatible streams); fall through to re-encode
        if out.exists():
            out.unlink()

    # Pass 2: high-quality re-encode (720p, 0.75fps, 48k audio)
    if out.exists():
        out.unlink()
    cmd2 = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video),
        "-vf", "fps=0.75,scale='-2':'min(720,ih)'",
        "-c:v", "libopenh264", "-allow_skip_frames", "1",
        "-c:a", "aac", "-ac", "1", "-b:a", "48k",
        str(out),
    ]
    ok2, err2 = run_ffmpeg(cmd2)
    if ok2 and out.exists():
        if file_mb(out) <= max_mb:
            return "re_encoded", out
    else:
        if out.exists():
            out.unlink()

    # Pass 3: moderate re-encode (640p, 0.5fps, 48k audio)
    if out.exists():
        out.unlink()
    cmd3 = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video),
        "-vf", "fps=0.5,scale='-2':'min(640,ih)'",
        "-c:v", "libopenh264", "-allow_skip_frames", "1",
        "-c:a", "aac", "-ac", "1", "-b:a", "48k",
        str(out),
    ]
    ok3, err3 = run_ffmpeg(cmd3)
    if ok3 and out.exists():
        if file_mb(out) <= max_mb:
            return "re_encoded", out
    else:
        if out.exists():
            out.unlink()

    # Pass 4: aggressive re-encode (480p, 0.3fps, 48k audio)
    if out.exists():
        out.unlink()
    cmd4 = [
        "ffmpeg", "-y",
        "-ss", str(start), "-to", str(end),
        "-i", str(video),
        "-vf", "fps=0.3,scale='-2':'min(480,ih)'",
        "-c:v", "libopenh264", "-allow_skip_frames", "1",
        "-c:a", "aac", "-ac", "1", "-b:a", "48k",
        str(out),
    ]
    ok4, err4 = run_ffmpeg(cmd4)
    if ok4 and out.exists():
        if file_mb(out) <= max_mb:
            return "re_encoded", out
        # Still over limit
        return "oversize", out

    # All passes failed
    if out.exists():
        out.unlink()
    return "error", None


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def process_segment(
    seg: dict,
    video: Path,
    out_dir: Path,
    digits: int,
    max_mb: int,
    total: int,
) -> dict:
    """Process a single segment; returns updated segment dict."""
    seg_id = seg["segment_id"]
    section = seg.get("section", {})
    start = section.get("start_seconds")
    end = section.get("end_seconds")

    filename = f"section_{seg_id:0{digits}d}.mp4"
    out_path = out_dir / filename

    # Skip non-visual segments
    if not seg.get("has_visual", True) or seg.get("keyframe") is None:
        seg["clip_path"] = None
        seg["clip_status"] = "no_visual"
        print(
            f"  section {seg_id:0{digits}d}/{total}: no_visual",
            file=sys.stderr,
        )
        return seg

    if start is None or end is None:
        seg["clip_path"] = None
        seg["clip_status"] = "error"
        print(
            f"  section {seg_id:0{digits}d}/{total}: error (missing timestamps)",
            file=sys.stderr,
        )
        return seg

    status, clip = extract_clip(video, start, end, out_path, max_mb)

    if clip is not None:
        seg["clip_path"] = str(clip)
        seg["clip_status"] = status
        size_mb = file_mb(clip)
        print(
            f"  section {seg_id:0{digits}d}/{total}: {status} ({size_mb:.1f} MB)",
            file=sys.stderr,
        )
    else:
        seg["clip_path"] = None
        seg["clip_status"] = status
        print(
            f"  section {seg_id:0{digits}d}/{total}: {status}",
            file=sys.stderr,
        )

    return seg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract per-section video clips from a lecture",
    )
    parser.add_argument(
        "segments_json",
        help="Path to segments.json produced by lecture-fusion.py",
    )
    parser.add_argument(
        "video",
        help="Path to source video (overrides segments.json video field)",
    )
    parser.add_argument(
        "--output-dir",
        default="clips",
        help="Output directory for clips (default: clips/)",
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        default=15,
        help="Max clip size in MB (default: 15)",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=None,
        help="Zero-pad width for filenames (default: auto from total_segments)",
    )
    args = parser.parse_args()

    segments_path = Path(args.segments_json)
    if not segments_path.exists():
        panic(f"file not found: {args.segments_json}")

    with segments_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Resolve video path
    video_arg = Path(args.video)
    if video_arg.exists():
        video = video_arg
    else:
        # Try relative to segments.json location
        video = segments_path.parent / video_arg
        if not video.exists():
            panic(f"video not found: {args.video}")

    # Also respect segments.json "video" field if CLI arg is not found directly
    json_video = data.get("video")
    if json_video and not video_arg.exists():
        candidate = Path(json_video)
        if not candidate.is_absolute():
            candidate = segments_path.parent / candidate
        if candidate.exists():
            video = candidate

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = data.get("total_segments", 0)
    digits = args.digits
    if digits is None:
        digits = 3 if total >= 100 else 2

    segments = data.get("segments", [])
    if not segments:
        panic("no segments found in segments.json")

    print(
        f"Extracting {len(segments)} clips from {video.name} → {out_dir}/",
        file=sys.stderr,
    )

    # Parallel extraction
    max_workers = min(4, len(segments))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                process_segment,
                seg,
                video,
                out_dir,
                digits,
                args.max_mb,
                total,
            ): seg
            for seg in segments
        }
        updated = []
        for future in concurrent.futures.as_completed(futures):
            updated.append(future.result())

    # Preserve original order
    updated.sort(key=lambda s: s["segment_id"])
    data["segments"] = updated

    # Write updated segments.json in-place
    with segments_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Done. Updated {segments_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
