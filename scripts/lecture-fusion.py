#!/usr/bin/env python3
"""Fuse transcript sections with video scenes into unified segments.

Usage:
  lecture-fusion.py sections.json scenes.json transcript.srt [-o DIR] [--digits N]

Reads sections.json (Phase 3) + scenes.json (Phase 2) + SRT transcript.
For each section: finds best-matching scene, extracts per-section frame,
copies section metadata, extracts transcript excerpt. Output: segments.json.

Key behaviors:
- Per-section frames extracted at section midpoint (not scene midpoint).
  Prevents all sections sharing one frame when a whiteboard scene spans many.
- Transcript excerpt padded: 15s before, 5s after section boundaries.
- Self-contained output: segment includes keyframe, has_visual, section fields
  — no separate file join needed at Phase 7.
- Frame naming: frame_NNN.jpg for first use of a scene, frame_NNNa/b/c.jpg
  for variant per-section extractions of the same scene.
"""

import argparse, json, re, subprocess, sys
from pathlib import Path

EXTEND_BACK = 15; EXTEND_FWD = 5

def panic(msg): print(f"Error: {msg}", file=sys.stderr); sys.exit(1)

def parse_srt(path):
    cues = []
    with open(path) as f: txt = f.read()
    for m in re.finditer(r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d+)\s*-->\s*'
                         r'(\d{2}):(\d{2}):(\d{2}),(\d+)\n((?:(?!\n\n).)*)', txt, re.DOTALL):
        start = int(m[2])*3600+int(m[3])*60+int(m[4])+int(m[5])/1000
        end = int(m[6])*3600+int(m[7])*60+int(m[8])+int(m[9])/1000
        cues.append({"s": round(start,3), "e": round(end,3),
                      "t": m[10].replace('\n',' ').strip()})
    return cues

def excerpt(cues, t0, t1):
    lines = []
    for c in cues:
        if c["s"] >= t0 and c["e"] <= t1:
            m, s = divmod(int(c["s"]), 60); lines.append(f"[{m:02d}:{s:02d}] {c['t']}")
    return "\n".join(lines)

def best_scene(t0, t1, scenes):
    best, best_o = None, 0
    for sc in scenes:
        o = max(0, min(t1, sc["end_seconds"]) - max(t0, sc["start_seconds"]))
        if o > best_o: best_o, best = o, sc
    return best

def frame_at(video, t, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",video,
                    "-frames:v","1","-q:v","2",str(path)], capture_output=True)
    return path if path.exists() else None

def hms(s): return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d}"

# --- main ---
def main():
    p = argparse.ArgumentParser()
    p.add_argument("sections"); p.add_argument("scenes"); p.add_argument("transcript")
    p.add_argument("-o","--output",default="segments.json"); p.add_argument("--digits",type=int,default=3)
    a = p.parse_args()

    with open(a.sections) as f: sd = json.load(f)
    with open(a.scenes) as f: scd = json.load(f)
    sections = sd["sections"]; scenes = scd["scenes"]
    video = scd["video"]; dur = scd["duration_seconds"]; cues = parse_srt(a.transcript)

    out = Path(a.output); kd = out.parent/"keyframes"; kd.mkdir(parents=True, exist_ok=True)
    d = a.digits

    segments = []
    scene_use_count = {}
    for sec in sections:
        sid = sec["section_id"]; t0 = sec["start_seconds"]; t1 = sec["end_seconds"]
        ms = best_scene(t0, t1, scenes)
        if not ms:
            # no visual match — still extract frame at midpoint as best effort
            fn = f"frame_{sid:0{d}}.jpg"
            frame_at(video, (t0+t1)/2, kd/fn)
            seg = {"segment_id": sid, "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
                   "scene": None, "keyframe": str(kd/fn) if (kd/fn).exists() else None,
                   "has_visual": False, "transcript_excerpt": excerpt(cues, t0, t1)}
            segments.append(seg); continue

        scid = ms["scene_id"]
        cnt = scene_use_count.get(scid, 0); scene_use_count[scid] = cnt + 1

        # First use of this scene → frame at section start. Reuse → variant suffix.
        fn = f"frame_{scid:0{d}}{chr(ord('a')+cnt) if cnt else ''}.jpg"
        frame_at(video, t0, kd/fn)
        kf = str(kd/fn) if (kd/fn).exists() else None

        seg = {
            "segment_id": sid,
            "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
            "scene": ms,
            "keyframe": kf,
            "has_visual": kf is not None,
            "transcript_excerpt": excerpt(cues, max(0,t0-EXTEND_BACK), min(dur,t1+EXTEND_FWD)),
        }
        segments.append(seg)

    out.write_text(json.dumps({
        "video": video, "duration_seconds": dur,
        "total_segments": len(segments),
        "lecture": sd.get("lecture",{}),
        "global_tags": sd.get("global_tags", []),
        "references_mentioned": sd.get("references_mentioned", []),
        "segments": segments,
    }, indent=2, ensure_ascii=False))
    print(f"Done. {len(segments)} segments → {out}", file=sys.stderr)

if __name__ == "__main__": main()
