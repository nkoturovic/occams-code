#!/usr/bin/env python3
"""Scene detection + keyframe extraction for lecture videos.

Usage:
  lecture-scenes.py <video> [-t THRESHOLD] [-o DIR] [--digits N]

Threshold: 0.30 slides, 0.15 whiteboard, 0.10 screencast, >0.40 animations.
Quality gate: count 6-40, max_duration < total/3, median < total/8.
Fail → auto-retune (step 0.05, max 3 retries) → accept best + warn.

Output: scenes.json + keyframes/frame_NNN.jpg (3-digit zero-padded).
"""

import argparse, json, re, statistics, subprocess, sys
from pathlib import Path

MIN_DEDUP_GAP = 3.0  # seconds — prevents presentation-switch transients

def panic(msg): print(f"Error: {msg}", file=sys.stderr); sys.exit(1)

def probe(video):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration,format_name,size",
                        "-of","json",video], capture_output=True, text=True)
    if r.returncode: panic(f"ffprobe: {r.stderr.strip()}")
    f = json.loads(r.stdout)["format"]
    return {"dur": float(f["duration"]), "fmt": f["format_name"], "size": int(f["size"])}

def detect(video, thresh):
    r = subprocess.run(["ffmpeg","-i",video,"-vf",f"select='gt(scene,{thresh})',showinfo",
                        "-f","null","-"], capture_output=True, text=True)
    ts = [float(m.group(1)) for line in r.stderr.split("\n")
          if (m := re.search(r"pts_time:([0-9.]+)", line))]
    if not ts or ts[0] > 1.0: ts.insert(0, 0.0)
    dedup = [ts[0]]
    for t in ts[1:]:
        if t - dedup[-1] >= MIN_DEDUP_GAP: dedup.append(t)
    return dedup

def scenes_from_ts(ts, total):
    return [{"scene_id": i+1, "start_seconds": round(ts[i],2),
             "end_seconds": round(ts[i+1] if i+1<len(ts) else total,2),
             "midpoint_seconds": round((ts[i]+(ts[i+1] if i+1<len(ts) else total))/2,2)}
            for i in range(len(ts))]

def gate_ok(scenes, total):
    if not scenes: return False
    d = [s["end_seconds"]-s["start_seconds"] for s in scenes]
    return 6 <= len(scenes) <= 40 and max(d) < total/3 and statistics.median(d) < total/8

def periodic(total, interval=10):
    n = max(6, int(total/interval)); return scenes_from_ts([i*interval for i in range(n)], total)

def keyframe(video, t, out):
    subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",video,
                    "-frames:v","1","-q:v","2",out], check=True)

def hms(s): return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d}"

# --- main ---
def main():
    p = argparse.ArgumentParser()
    p.add_argument("video"); p.add_argument("-t","--threshold",type=float,default=0.30)
    p.add_argument("-o","--output",default="."); p.add_argument("--digits",type=int,default=3)
    a = p.parse_args()
    vp = Path(a.video)
    if not vp.exists(): panic(f"not found: {a.video}")
    od = Path(a.output).resolve(); kd = od/"keyframes"; kd.mkdir(parents=True,exist_ok=True)
    meta = probe(str(vp)); dur = meta["dur"]
    print(f"Video: {vp.name} ({dur/60:.1f}min)", file=sys.stderr)

    thresh = a.threshold; best = None; retries = 0
    for attempt in range(4):
        sc = scenes_from_ts(detect(str(vp), thresh), dur)
        gk = gate_ok(sc, dur)
        durs = [s["end_seconds"]-s["start_seconds"] for s in sc]
        print(f"  threshold={thresh:.2f}: {len(sc)} scenes max={max(durs or[0]):.0f}s"
              f" median={statistics.median(durs or[0]):.0f}s → {'PASS' if gk else 'FAIL'}", file=sys.stderr)
        if gk: best = sc; break
        if not best or max(durs) < max([s["end_seconds"]-s["start_seconds"] for s in best] or [0]): best = sc
        retries = attempt
        if attempt < 3 and thresh - 0.05 >= 0.05: thresh = round(thresh-0.05, 2)
        else: break

    if not best or len(best) < 6:
        print(f"  → fallback periodic sampling", file=sys.stderr); best = periodic(dur)
    elif retries: print(f"  → accepted at {thresh:.2f} after {retries} retries", file=sys.stderr)

    print(f"Extracting {len(best)} keyframes...", file=sys.stderr)
    for s in best:
        fn = f"frame_{s['scene_id']:0{a.digits}d}.jpg"
        keyframe(str(vp), s["midpoint_seconds"], str(kd/fn))
        s["keyframe"] = str(kd/fn); s["start_time"] = hms(s["start_seconds"]); s["end_time"] = hms(s["end_seconds"])

    manifest = {"video":str(vp.resolve()),"duration_seconds":round(dur,2),
                "threshold_used":thresh,"threshold_initial":a.threshold,"retries":retries,"scenes":best}
    (od/"scenes.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    print(f"Done → {od/'scenes.json'}", file=sys.stderr)

if __name__ == "__main__": main()
