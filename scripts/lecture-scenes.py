#!/usr/bin/env python3
"""Scene detection + keyframe extraction for lecture videos.

Usage:
  lecture-scenes.py <video> [-t THRESHOLD] [-o DIR] [--min-duration SEC] [--digits N]

Threshold: 0.25 slides, 0.05 whiteboard, 0.10 screencast, >0.40 animations.
Quality gate: n_min–n_max scenes (n_min = max(12, dur/300), n_max = max(60, dur/180)), max_duration < total/2, median < total/8.
Fail → auto-retune (step 0.05, max 3 retries) → accept best + warn.

Post-detect merge: scenes shorter than --min-duration are absorbed into the
PREVIOUS scene (not longer neighbor). Default 8s — catches PowerPoint transition
flickers, cursor movements, and taskbar overlays that ffmpeg scene-detect falsely
registers as scene changes. Preserves meaningful content boundaries while
eliminating noise.

Output: scenes.json + keyframes/frame_NNN.jpg (3-digit zero-padded).
"""

import argparse, json, re, statistics, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    if r.returncode:
        panic(f"ffmpeg scene detect failed (rc={r.returncode}): {r.stderr.strip()[:200]}")
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
    n_min = max(12, int(total / 300))  # at least 12, +1 per 5 minutes
    n_max = max(60, int(total / 180))  # at least 60, +1 per 3 minutes
    return n_min <= len(scenes) <= n_max and max(d) < total/2 and statistics.median(d) < total/8

def periodic(total):
    """Fallback: periodic keyframes targeting ~5-minute intervals, minimum 12 scenes."""
    n = max(12, int(total / 300))
    interval = total / n
    return scenes_from_ts([round(i * interval, 1) for i in range(n)], total)

def merge_short(scenes, min_dur):
    """Absorb scenes shorter than min_dur into the PREVIOUS scene.
    Short scenes are always transition tail ends of the previous visual —
    the first frame(s) after a slide change belong to new content already.
    Re-numbers after merging. Runs iteratively until stable."""
    if len(scenes) <= 1: return scenes
    changed = True
    while changed:
        changed = False
        for i in range(len(scenes)-1, 0, -1):  # skip scene 0 — nothing to merge it into
            if scenes[i]["end_seconds"] - scenes[i]["start_seconds"] >= min_dur:
                continue
            # Absorb into previous scene: extend its end, this scene's content never began
            prev = i - 1
            scenes[prev]["end_seconds"] = scenes[i]["end_seconds"]
            scenes[prev]["midpoint_seconds"] = round(
                (scenes[prev]["start_seconds"] + scenes[prev]["end_seconds"]) / 2, 2)
            scenes.pop(i)
            changed = True
            break  # list mutated, restart outer loop
    for j, s in enumerate(scenes): s["scene_id"] = j + 1
    return scenes

def hms(s): return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d}"

# --- main ---
def main():
    p = argparse.ArgumentParser()
    p.add_argument("video"); p.add_argument("-t","--threshold",type=float,default=0.25)
    p.add_argument("-o","--output",default="scenes.json"); p.add_argument("--digits",type=int,default=3)
    p.add_argument("--min-duration",type=float,default=8.0,
                   help="Merge scenes shorter than this (seconds) into neighbours (default 8)")
    a = p.parse_args()
    vp = Path(a.video)
    if not vp.exists(): panic(f"not found: {a.video}")

    # -o specifies the output JSON file path (default: scenes.json in CWD).
    # Keyframes go to {json_parent}/keyframes/.
    out = Path(a.output)
    od = out.parent; json_name = out.name
    kd = od/"keyframes"; kd.mkdir(parents=True,exist_ok=True)
    meta = probe(str(vp)); dur = meta["dur"]
    n_min = max(12, int(dur / 300))
    n_max = max(60, int(dur / 180))
    print(f"Video: {vp.name} ({dur/60:.1f}min)", file=sys.stderr)

    thresh = a.threshold; best = None; best_thresh = thresh; retries = 0; passed = False
    for attempt in range(4):
        sc = scenes_from_ts(detect(str(vp), thresh), dur)
        gk = gate_ok(sc, dur)
        durs = [s["end_seconds"]-s["start_seconds"] for s in sc]
        print(f"  threshold={thresh:.2f}: {len(sc)} scenes max={max(durs or[0]):.0f}s"
              f" median={statistics.median(durs or[0]):.0f}s → {'PASS' if gk else 'FAIL'}", file=sys.stderr)
        if gk:
            best = sc; best_thresh = thresh; retries = attempt; passed = True; break
        if not best or max(durs) < max([s["end_seconds"]-s["start_seconds"] for s in best] or [0]):
            best = sc; best_thresh = thresh
        retries = attempt + 1
        if attempt < 3:
            if len(sc) > n_max:
                if thresh + 0.05 <= 0.60:
                    thresh = round(thresh+0.05, 2)    # too many tiny fragments → raise
                else: break                           # capped at 0.60, accept best-so-far
            elif len(sc) < n_min:
                if thresh - 0.05 >= 0.05:
                    thresh = round(thresh-0.05, 2)     # too few → lower
                else: break
            else: break                                # max(d) or median(d) issue → threshold won't help
        else: break

    if not best or len(best) < 6:
        print(f"  → fallback periodic sampling (count fail)", file=sys.stderr)
        best = periodic(dur); best_thresh = "fallback"; retries = 0; passed = False
    elif passed:
        rs = "retry" if retries == 1 else "retries"
        print(f"  → accepted at {best_thresh:.2f}" + (f" after {retries} {rs}" if retries else ""), file=sys.stderr)
    else:
        # Max duration or median failed — periodic beats best-effort for continuous content
        durs = [s["end_seconds"]-s["start_seconds"] for s in best]
        if max(durs) > dur/2:
            print(f"  → fallback periodic sampling (max scene {max(durs):.0f}s > {dur/2:.0f}s)", file=sys.stderr)
            best = periodic(dur); best_thresh = "fallback"; retries = 0; passed = False
        else:
            print(f"  → best-effort at {best_thresh:.2f} (gate failed — {len(best)} scenes)", file=sys.stderr)

    # Merge flicker scenes (PPT transitions, cursor overlays) into neighbors.
    # Default 8s threshold catches 100% of observed noise across 4 datasets.
    pre_merge = len(best)
    best = merge_short(best, a.min_duration)
    if pre_merge != len(best):
        print(f"  merged {pre_merge} → {len(best)} scenes (min-duration={a.min_duration}s)", file=sys.stderr)

    # Write scenes.json IMMEDIATELY — before extraction.
    # If extraction times out, timestamps survive.
    for s in best:
        s["start_time"] = hms(s["start_seconds"]); s["end_time"] = hms(s["end_seconds"])
        s["keyframe"] = str(kd / f"frame_{s['scene_id']:0{a.digits}d}.jpg")
    manifest = {"video":str(vp.resolve()),"duration_seconds":round(dur,2),
                "threshold_used":best_thresh,"threshold_initial":a.threshold,"retries":retries,
                "min_duration":a.min_duration,"scenes":best}
    (od/json_name).write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    print(f"  {json_name} written ({len(best)} scenes)", file=sys.stderr)

    # Parallel keyframe extraction
    print(f"Extracting {len(best)} keyframes...", file=sys.stderr)
    def _extract(s):
        fn = f"frame_{s['scene_id']:0{a.digits}d}.jpg"
        path = str(kd/fn); t = s["midpoint_seconds"]
        subprocess.run(["ffmpeg","-y","-v","error","-ss",str(t),"-i",str(vp),
                        "-frames:v","1","-q:v","2",path], check=True)
        return s["scene_id"]

    with ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(_extract, s): s for s in best}
        failed = []
        for i, f in enumerate(as_completed(futs), 1):
            try:
                sid = f.result()
                print(f"  keyframe {i}/{len(best)} (scene {sid})", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                sid = futs[f]["scene_id"]
                failed.append(sid)
                print(f"  keyframe {i}/{len(best)} (scene {sid}) FAILED: {e.stderr.strip()[:120] if e.stderr else e}"
                      , file=sys.stderr)

    if failed:
        print(f"Warning: {len(failed)} keyframe extraction(s) failed: scenes {failed}", file=sys.stderr)
        sys.exit(1)

    print(f"Done → {od/json_name}", file=sys.stderr)

if __name__ == "__main__": main()
