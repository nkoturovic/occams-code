#!/usr/bin/env python3
"""Apply transcript_corrections from segments_analyzed.json to an SRT file.

Usage:
  correct-transcript.py segments_analyzed.json transcript.srt [-o OUTPUT.srt] [--dry-run]

Reads Phase 5 output (segments_analyzed.json) and a whisper.cpp SRT transcript.
Each segment may contain a transcript_corrections list. For each correction,
finds the SRT entry whose text contains the garbled transcript string
(case-insensitive substring match) and whose start time is closest to the
correction timestamp. Replaces that entry's text with the corrected text.

Safety constraints:
- Timestamps are never modified.
- Entry numbers are never modified.
- Blank lines separating entries are preserved.
- Only the text portion of matching entries is edited.
- If no match is found, the correction is skipped with a warning.
"""

import argparse
import json
import re
import sys

SRT_RE = re.compile(
    r'(\d+)\n'
    r'(\d{2}):(\d{2}):(\d{2}),(\d+)\s*-->\s*'
    r'(\d{2}):(\d{2}):(\d{2}),(\d+)\n'
    r'((?:(?!\n\n).)*)',
    re.DOTALL,
)


def panic(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_time_to_seconds(ts: str) -> float:
    """Parse 'MM:SS' → seconds (float)."""
    parts = ts.split(':')
    if len(parts) != 2:
        panic(f"Invalid correction time format: {ts!r} (expected MM:SS)")
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except ValueError:
        panic(f"Invalid correction time format: {ts!r} (expected numeric MM:SS)")


def parse_srt_entries(text: str):
    """Parse SRT text and return list of dicts with match info."""
    entries = []
    for m in SRT_RE.finditer(text):
        start_s = int(m[2]) * 3600 + int(m[3]) * 60 + int(m[4]) + int(m[5]) / 1000
        entries.append({
            "match": m,
            "index": int(m[1]),
            "start": start_s,
            "text": m[10],
            "text_start": m.start(10),
            "text_end": m.end(10),
        })
    return entries


def collect_corrections(segments):
    """Extract all corrections from segments list."""
    corrections = []
    required_keys = {"time", "transcript", "correction"}
    for seg in segments:
        for c in seg.get("transcript_corrections", []):
            if not c:
                continue
            if not required_keys.issubset(c):
                print(
                    f"Warning: skipping malformed correction {c!r}",
                    file=sys.stderr,
                )
                continue
            corrections.append(c)
    return corrections


def main():
    parser = argparse.ArgumentParser(
        description="Apply transcript corrections from segments_analyzed.json to an SRT file."
    )
    parser.add_argument("segments_json", help="Path to segments_analyzed.json")
    parser.add_argument("transcript_srt", help="Path to transcript.srt")
    parser.add_argument("-o", "--output", help="Write corrected SRT to this file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print proposed changes to stdout, do not write output file",
    )
    args = parser.parse_args()

    # --- Load inputs ---
    try:
        with open(args.segments_json, encoding="utf-8") as f:
            segments = json.load(f)
    except Exception as e:
        panic(f"Cannot read {args.segments_json}: {e}")

    try:
        with open(args.transcript_srt, encoding="utf-8") as f:
            srt_text = f.read()
    except Exception as e:
        panic(f"Cannot read {args.transcript_srt}: {e}")

    if not isinstance(segments, list):
        panic(f"Expected {args.segments_json} to contain a JSON list of segments")

    corrections = collect_corrections(segments)
    entries = parse_srt_entries(srt_text)

    if not entries:
        panic(f"No SRT entries found in {args.transcript_srt}")

    # --- Match corrections to entries ---
    applied = 0
    unmatched = 0
    # Per-entry accumulated corrections: entry_index → list of (transcript_query, correction_text)
    entry_corrections = {}
    # For dry-run reporting: entry_index → original text
    dry_run_before = {}

    for c in corrections:
        target_time = parse_time_to_seconds(c["time"])
        transcript_query = c["transcript"]
        correction_text = c["correction"]

        candidates = []
        for i, e in enumerate(entries):
            if transcript_query.lower() in e["text"].lower():
                candidates.append((abs(e["start"] - target_time), i))

        if not candidates:
            unmatched += 1
            print(
                f"Warning: no match for {transcript_query!r} at ~{c['time']}",
                file=sys.stderr,
            )
            continue

        candidates.sort(key=lambda x: x[0])
        best_i = candidates[0][1]
        e = entries[best_i]

        if best_i not in entry_corrections:
            entry_corrections[best_i] = []
            if args.dry_run:
                dry_run_before[best_i] = e["text"]
        entry_corrections[best_i].append((transcript_query, correction_text))
        applied += 1

    # --- Apply corrections per entry (substring replacement, case-insensitive) ---
    # Build replacement map: text_start → new full text for that entry
    replacements = {}
    dry_run_log = []

    for i, corrections_for_entry in entry_corrections.items():
        e = entries[i]
        new_text = e["text"]
        for transcript_query, correction_text in corrections_for_entry:
            new_text = re.sub(
                re.escape(transcript_query),
                correction_text,
                new_text,
                count=1,
                flags=re.IGNORECASE,
            )
        if new_text != e["text"]:
            replacements[e["text_start"]] = (e["text_start"], e["text_end"], new_text)
            if args.dry_run:
                dry_run_log.append(
                    f"[Entry #{e['index']} ({len(corrections_for_entry)} correction(s))]\n"
                    f"  - before: {dry_run_before[i]!r}\n"
                    f"  + after:  {new_text!r}"
                )

    # --- Apply replacements (work backwards to preserve positions) ---
    sorted_replacements = sorted(replacements.values(), key=lambda r: r[0], reverse=True)
    result = srt_text
    for start, end, new_text in sorted_replacements:
        result = result[:start] + new_text + result[end:]

    # --- Output ---
    total = len(corrections)
    if args.dry_run:
        if dry_run_log:
            print("\n".join(dry_run_log))
        print(
            f"Would apply {applied}/{total} corrections ({unmatched} unmatched)",
            file=sys.stderr,
        )
        return

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result)
        except Exception as e:
            panic(f"Cannot write {args.output}: {e}")
    else:
        sys.stdout.write(result)

    print(
        f"Applied {applied}/{total} corrections ({unmatched} unmatched)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
