"""Makes the forest flight's in-between frames by motion interpolation, where only every other frame
was rendered (python3 tools/video/fill_frames.py). Writes build/video/exterior-interp/NNNN.png for each
missing frame; compose.py uses those until a real render of that frame exists in build/video/exterior/.
"""
import glob
import os
import shutil
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXT = os.path.join(ROOT, "build", "video", "exterior")
OUT = os.path.join(ROOT, "build", "video", "exterior-interp")
have = sorted(int(os.path.basename(f)[:4]) for f in glob.glob(os.path.join(EXT, "[0-9][0-9][0-9][0-9].png")))
os.makedirs(OUT, exist_ok=True)
# runs of frames rendered two apart: interpolate each run at double rate
runs, cur = [], [have[0]]
for a, b in zip(have, have[1:]):
    if b - a == 2:
        cur.append(b)
    else:
        if len(cur) > 1:
            runs.append(cur)
        cur = [b]
if len(cur) > 1:
    runs.append(cur)
for run in runs:
    tmp = tempfile.mkdtemp()
    for i, k in enumerate(run):
        os.symlink(os.path.join(EXT, f"{k:04d}.png"), os.path.join(tmp, f"{i:04d}.png"))
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-framerate", "12", "-i", os.path.join(tmp, "%04d.png"),
                    "-vf", "minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1", os.path.join(tmp, "m%04d.png")], check=True)
    made = 0
    for j in range(1, 2 * (len(run) - 1), 2):                 # the odd outputs are the in-between frames
        src = os.path.join(tmp, f"m{j + 1:04d}.png")          # (ffmpeg numbers its outputs from 1)
        k = run[0] + j
        if os.path.exists(src) and not os.path.exists(os.path.join(EXT, f"{k:04d}.png")):
            shutil.copy(src, os.path.join(OUT, f"{k:04d}.png"))
            made += 1
    shutil.rmtree(tmp)
    print(f"frames {run[0]}-{run[-1]}: {made} in-between frames made")
