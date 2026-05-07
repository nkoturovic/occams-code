#!/usr/bin/env python3
"""Fuse transcript sections with video scenes into unified segments.

Usage:
  lecture-fusion.py sections.json scenes.json transcript.srt [-o DIR] [--digits N]

Reads sections.json (Phase 3) + scenes.json (Phase 2) + SRT transcript.
For each section: finds best-matching scene, extracts per-section frame(s),
copies section metadata, extracts transcript excerpt. Output: segments.json.

Per-section frame selection:
- Extracts 3 candidate frames at 25%, 50%, 75% of section→scene overlap.
- Picks the candidate with largest JPEG file size (most visual content).
- For whiteboard lectures: avoids blank/transition frames at section edges.
- For slide lectures: all candidates show the same slide — any is fine.

Key behaviors:
- Frames extracted within scene overlap, not at scene midpoint.
- Transcript excerpt padded: 15s before, 5s after section boundaries.
- Self-contained output: segment includes keyframe, has_visual, section fields.
- Frame naming: variant suffix (frame_NNNa/b/c.jpg), never overwrites
  Phase 2 scene-midpoint keyframes.
"""

import argparse, json, re, shutil, subprocess, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EXTEND_BACK = 15; EXTEND_FWD = 5
CANDIDATE_FRACTIONS = [0.25, 0.50, 0.75]  # through section→scene overlap window
MIN_VISUAL_BYTES = 50_000  # smallest observed content frame: ~75KB; blank frames: ~34KB

def panic(msg): print(f"Error: {msg}", file=sys.stderr); sys.exit(1)

# --- SRT parsing ---

def parse_srt(path):
    cues = []
    with open(path) as f: txt = f.read()
    for m in re.finditer(r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d+)\s*-->\s*'
                         r'(\d{2}):(\d{2}):(\d{2}),(\d+)\n((?:(?!\n\n).)*)', txt, re.DOTALL):
        start = int(m[2])*3600+int(m[3])*60+int(m[4])+int(m[5])/1000
        end   = int(m[6])*3600+int(m[7])*60+int(m[8])+int(m[9])/1000
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

# --- Frame extraction ---

def frame_at(video, t, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",video,
                        "-frames:v","1","-q:v","2",str(path)], capture_output=True)
    if r.returncode:
        print(f"  ffmpeg error for {path.name}: {r.stderr.decode(errors='replace').strip()[:120]}",
              file=sys.stderr)
    return path if path.exists() else None

def select_best(candidates):
    """Pick the candidate path with largest JPEG file size.
    Larger file → more visual information (blank board compresses smaller).
    Returns None if no candidates survived extraction."""
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_size)

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

    # ── Phase A: Plan — canonical filenames + candidate extraction times ──

    tasks = []; scene_use_count = {}
    for sec in sections:
        sid, t0, t1 = sec["section_id"], sec["start_seconds"], sec["end_seconds"]
        ms = best_scene(t0, t1, scenes)
        if ms is None:
            fn = f"frame_{sid:0{d}}.jpg"
            tasks.append(dict(sid=sid, sec=sec, ms=None,
                              canonical_fn=fn,
                              candidate_times=[(t0 + t1) / 2]))
            continue
        scid = ms["scene_id"]
        cnt = scene_use_count.get(scid, 0); scene_use_count[scid] = cnt + 1
        fn = f"frame_{scid:0{d}}{chr(ord('a') + cnt)}.jpg"
        ov0 = max(t0, ms["start_seconds"]); ov1 = min(t1, ms["end_seconds"])
        ov_dur = ov1 - ov0
        candidate_times = [round(ov0 + ov_dur * f, 1) for f in CANDIDATE_FRACTIONS]
        tasks.append(dict(sid=sid, sec=sec, ms=ms,
                          canonical_fn=fn,
                          candidate_times=candidate_times))

    # ── Phase B: Extract all candidates to temp dir ──

    tmpdir = out.parent / "_tmp_fusion"; tmpdir.mkdir(parents=True, exist_ok=True)
    total = sum(len(t["candidate_times"]) for t in tasks)

    candidates_by_canon = defaultdict(list)  # canonical_fn → [(tmp_path, sid)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {}
        for task in tasks:
            for ci, t in enumerate(task["candidate_times"]):
                stem = task["canonical_fn"].rsplit(".", 1)[0]
                tmp_path = tmpdir / f"{stem}_c{ci}.jpg"
                futs[ex.submit(frame_at, video, t, tmp_path)] = (task["sid"], task["canonical_fn"], tmp_path)

        for i, f in enumerate(as_completed(futs), 1):
            sid, canon_fn, tmp_path = futs[f]
            result = f.result()
            if result is not None:
                candidates_by_canon[canon_fn].append(result)
            print(f"  frame {i}/{total}", file=sys.stderr)

    # ── Phase C: Select best per section (largest JPEG) → keyframes/ ──

    for task in tasks:
        canon_fn = task["canonical_fn"]
        best = select_best(candidates_by_canon.get(canon_fn, []))
        if best is not None:
            canon_path = kd / canon_fn
            shutil.copy2(best, canon_path)
            # Blank-frame check: black/empty frames compress far smaller than any
            # real content frame (lowest content observed: ~75KB; blank: ~34KB).
            task["keyframe_path"] = canon_path if canon_path.stat().st_size >= MIN_VISUAL_BYTES else None
        else:
            task["keyframe_path"] = None

    shutil.rmtree(tmpdir, ignore_errors=True)

    # ── Phase D: Build segments ──

    segments = []
    for task in tasks:
        sid = task["sid"]; sec = task["sec"]; ms = task["ms"]
        t0, t1 = sec["start_seconds"], sec["end_seconds"]
        kp = task["keyframe_path"]
        kp_str = str(kp) if (kp and kp.exists()) else None
        if ms is None:
            seg = {"segment_id": sid,
                   "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
                   "scene": None,
                   "keyframe": kp_str,
                   "has_visual": False,
                   "transcript_excerpt": excerpt(cues, t0, t1)}
        else:
            seg = {"segment_id": sid,
                   "section": {**sec, "start_time": hms(t0), "end_time": hms(t1)},
                   "scene": ms,
                   "keyframe": kp_str,
                   "has_visual": kp is not None and kp.exists(),
                   "transcript_excerpt": excerpt(cues, max(0, t0-EXTEND_BACK), min(dur, t1+EXTEND_FWD))}
        segments.append(seg)

    out.write_text(json.dumps({
        "video": video, "duration_seconds": dur,
        "total_segments": len(segments),
        "lecture": sd.get("lecture", {}),
        "global_tags": sd.get("global_tags", []),
        "segments": segments,
    }, indent=2, ensure_ascii=False))
    print(f"Done. {len(segments)} segments → {out}", file=sys.stderr)


if __name__ == "__main__": main()
