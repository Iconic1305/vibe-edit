"""Visual + audio analysis of a take with FFmpeg (no AI model needed).

Usage:
    python3 scripts/analyze_video.py projects/<slug>/input/take.mp4 [--fps 1]

Writes work/<name>.analysis.json:
  * stream facts: size, fps, rotation, duration, audio present
  * per-sample brightness and motion (frame difference) -> too dark / frozen / busy spots
  * hard scene cuts (select='gt(scene,0.35)')
  * silences (silencedetect) and loudness (volumedetect)
  * flags: plain-language warnings Claude should act on before building
Claude also LOOKS at the frames (extract_frames.py contact sheet) for what FFmpeg can't judge:
where the face and hands are, what is behind the speaker, which areas are empty.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from common import probe_duration, require, save_json, work_dir


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def streams(video):
    p = run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(video)])
    return json.loads(p.stdout)["streams"]


def brightness_series(video, fps):
    """YAVG (mean luma 0-255) and a frame-difference score per sample."""
    p = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", f"fps={fps},scale=160:-2,signalstats,metadata=print:file=-",
             "-an", "-f", "null", "-"])
    ys = [float(m) for m in re.findall(r"lavfi\.signalstats\.YAVG=([\d.]+)", p.stdout)]
    diff = [float(m) for m in re.findall(r"lavfi\.signalstats\.YDIF=([\d.]+)", p.stdout)]
    return ys, diff


def scene_cuts(video):
    p = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "select='gt(scene,0.35)',showinfo", "-an", "-f", "null", "-"])
    return [round(float(t), 2) for t in re.findall(r"pts_time:([\d.]+)", p.stderr)]


def audio_facts(video):
    sil = run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "silencedetect=noise=-35dB:d=0.4", "-vn", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", sil.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", sil.stderr)]
    silences = [{"start": round(s, 2), "end": round(e, 2)} for s, e in zip(starts, ends)]
    vol = run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol.stderr)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", vol.stderr)
    return silences, (float(mean.group(1)) if mean else None), (float(peak.group(1)) if peak else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=1.0)
    a = ap.parse_args()
    require("ffmpeg"), require("ffprobe")
    video = Path(a.video)
    if not video.exists():
        sys.exit(f"Not found: {video}")

    st = streams(video)
    v = next((s for s in st if s["codec_type"] == "video"), None)
    au = next((s for s in st if s["codec_type"] == "audio"), None)
    if not v:
        sys.exit("No video stream found")
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    rotation = 0
    for sd in v.get("side_data_list", []):
        rotation = int(sd.get("rotation", rotation))
    w, h = v["width"], v["height"]
    if abs(rotation) in (90, 270):
        w, h = h, w
    duration = probe_duration(video)

    ys, dif = brightness_series(video, a.fps)
    silences, mean_db, peak_db = audio_facts(video) if au else ([], None, None)
    cuts = scene_cuts(video)

    flags = []
    if ys and sum(ys) / len(ys) < 60:
        flags.append("Footage is dark (mean luma < 60): light the face better or apply a grade.")
    if ys and sum(ys) / len(ys) > 200:
        flags.append("Footage is very bright (mean luma > 200): highlights may clip.")
    if dif and sum(dif) / len(dif) < 0.05:
        flags.append("Almost no frame-to-frame change: tripod shot or frozen video (fine for a talking head).")
    if not au:
        flags.append("No audio track: Whisper has nothing to transcribe.")
    elif mean_db is not None and mean_db < -32:
        flags.append(f"Audio is quiet (mean {mean_db} dB): normalise or re-record closer to the mic.")
    if peak_db is not None and peak_db > -0.5:
        flags.append("Audio peaks near 0 dB: possible clipping.")
    if num / den > 31 or abs(num / den - round(num / den)) > 0.01:
        flags.append(f"Frame rate is {num / den:.3f} fps: HyperFrames renders at 30 fps, so timing is resampled.")
    if len(cuts) > 0:
        flags.append(f"{len(cuts)} hard scene change(s) detected: check they are intended jump cuts.")

    out = save_json({
        "source": str(video), "duration": round(duration, 3),
        "video": {"width": w, "height": h, "orientation": "vertical" if h > w else "horizontal" if w > h else "square",
                  "fps": round(num / den, 3), "codec": v["codec_name"], "rotation": rotation},
        "audio": {"present": bool(au), "mean_volume_db": mean_db, "peak_volume_db": peak_db, "silences": silences},
        "luma": {"fps": a.fps, "mean": round(sum(ys) / len(ys), 1) if ys else None, "samples": ys},
        "motion": {"fps": a.fps, "mean_diff": round(sum(dif) / len(dif), 3) if dif else None, "samples": dif},
        "scene_cuts": cuts, "flags": flags,
    }, work_dir(video) / f"{video.stem}.analysis.json")

    print(f"{w}x{h} {'vertical' if h > w else 'horizontal' if w > h else 'square'} · {num / den:.2f} fps · {duration:.1f}s · "
          f"audio {'yes' if au else 'NO'}")
    for f in flags or ["No problems found."]:
        print(" -", f)
    print("Saved", out)


if __name__ == "__main__":
    main()
