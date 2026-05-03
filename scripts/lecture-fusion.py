#!/usr/bin/env python3
"""Fuse transcript sections with video scenes into unified segments.

Usage:
  lecture-fusion.py sections.json scenes.json transcript.srt [-o DIR] [--digits N]

Reads sections.json (Phase 3) + scenes.json (Phase 2) + SRT transcript.
For each section: finds best-matching scene, extracts per-section frame,
copies section metadata, extracts transcript excerpt. Output: segments.json.

Key behaviors:
- Per-section frames extracted at max(section_start, scene_start) — within scene.
  Prevents all sections sharing one frame when a whiteboard scene spans many.
- Transcript excerpt padded: 15s before, 5s after section boundaries.
- Self-contained output: segment includes keyframe, has_visual, section fields
  — no separate file join needed at Phase 7.
- Frame naming: always variant suffix (frame_NNNa/b/c.jpg). Never overwrites
  Phase 2 scene-midpoint keyframes.
"""

import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    r = subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",video,
                        "-frames:v","1","-q:v","2",str(path)], capture_output=True)
    if r.returncode:
        print(f"  ffmpeg failed for {path.name}: {r.stderr.decode(errors='replace').strip()[:120]}",
              file=sys.stderr)
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
    tasks = []  # (frame_fn, extract_time, section_info, scene_info)
    for sec in sections:
        sid = sec["section_id"]; t0 = sec["start_seconds"]; t1 = sec["end_seconds"]
        ms = best_scene(t0, t1, scenes)
        if not ms:
            fn = f"frame_{sid:0{d}}.jpg"
            tasks.append((fn, (t0+t1)/2, sid, sec, None))
            continue
        scid = ms["scene_id"]
        cnt = scene_use_count.get(scid, 0); scene_use_count[scid] = cnt + 1
        fn = f"frame_{scid:0{d}}{chr(ord('a')+cnt)}.jpg"
        tasks.append((fn, max(t0, ms["start_seconds"]), sid, sec, ms))

    # Parallel frame extraction
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(frame_at, video, t, kd/fn): (fn, sid) for fn, t, sid, *_ in tasks}
        for i, f in enumerate(as_completed(futs), 1):
            fn, sid = futs[f]
            f.result()  # exceptions handled inside frame_at via returncode check
            print(f"  frame {i}/{len(tasks)} (section {sid})", file=sys.stderr)

    # Build segments (sequential — depends on completed frames)
    for fn, t, sid, sec, ms in tasks:
        t0 = sec["start_seconds"]; t1 = sec["end_seconds"]
        kf_path = kd/fn
        if ms is None:
            seg = {"segment_id": sid, "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
                   "scene": None, "keyframe": str(kf_path) if kf_path.exists() else None,
                   "has_visual": False, "transcript_excerpt": excerpt(cues, t0, t1)}
        else:
            seg = {
                "segment_id": sid,
                "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
                "scene": ms,
                "keyframe": str(kf_path) if kf_path.exists() else None,
                "has_visual": kf_path.exists(),
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
