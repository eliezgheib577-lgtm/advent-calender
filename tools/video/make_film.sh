#!/usr/bin/env bash
# Builds the finished promo film from the rendered parts, start to end:
#   bash tools/video/make_film.sh [PYTHON_FOR_AUDIO]
# 1. the forest flight's in-between frames (fill_frames.py)
# 2. the picture, in four parts side by side (compose.py --frames --tag), then joined
# 3. the sound (audio.py; needs numpy, scipy, soundfile: pass that python as the first argument)
# 4. the masters, narrated and music-only, and WhatsApp copies of both (720p ~16 MB, 1080p ~40 MB)
# Writes build/video/out/; build/video/out/film.log says which step it is on.
set -euo pipefail
cd "$(dirname "$0")/../.."
PYA="${1:-python3}"
OUT=build/video/out
LOG=$OUT/film.log
mkdir -p "$OUT"
: > "$LOG"
step() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" | tee -a "$LOG"; }

step "fill"
python3 tools/video/fill_frames.py

step "compose"
N=$(python3 -c "import json; print(json.load(open('$OUT/cues.json'))['total'])" 2>/dev/null || echo 148.9)
FRAMES=$(python3 -c "print(int(round($N*24)))")
PARTS=4
pids=()
for i in $(seq 0 $((PARTS-1))); do
  a=$(( FRAMES * i / PARTS )); b=$(( FRAMES * (i+1) / PARTS - 1 ))
  python3 tools/video/compose.py --frames=$a-$b --tag=p$i > "$OUT/compose-p$i.log" 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
python3 - "$OUT" "$PARTS" <<'EOF'
import json, sys
out, parts = sys.argv[1], int(sys.argv[2])
cs = [json.load(open(f"{out}/cues-p{i}.json")) for i in range(parts)]
sfx = sorted({(c["sfx"], c["at"]) for p in cs for c in p["sfx"]}, key=lambda c: c[1])
merged = dict(cs[0], sfx=[{"sfx": s, "at": t} for s, t in sfx])
json.dump(merged, open(f"{out}/cues.json", "w"), indent=1)
print(len(sfx), "sound effects")
EOF
( for i in $(seq 0 $((PARTS-1))); do echo "file 'picture-p$i.mp4'"; done ) > "$OUT/parts.txt"
ffmpeg -y -hide_banner -loglevel error -f concat -safe 0 -i "$OUT/parts.txt" -c copy "$OUT/picture.mp4"

step "sound"
"$PYA" tools/video/audio.py

step "export"
for v in voice novoice; do
  name=$([ $v = voice ] && echo narrated || echo music-only)
  ffmpeg -y -hide_banner -loglevel error -i "$OUT/picture.mp4" -i "$OUT/mix-$v.wav" -map 0:v -map 1:a \
    -c:v copy -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT/LeMSIC-advent-$name.mp4"
done

step "whatsapp"
# two-pass so the size lands where it should; hqdn3d takes out the film grain, which costs bits and looks like noise when small
wa() {  # master, out, scale height, video kbps, audio kbps
  local pl="$OUT/pass-$(basename "$2" .mp4)"
  ffmpeg -y -hide_banner -loglevel error -i "$1" -vf "hqdn3d,scale=-2:$3:flags=lanczos" -c:v libx264 -preset slow \
    -b:v "$4k" -pass 1 -passlogfile "$pl" -an -f null /dev/null
  ffmpeg -y -hide_banner -loglevel error -i "$1" -vf "hqdn3d,scale=-2:$3:flags=lanczos" -c:v libx264 -preset slow \
    -b:v "$4k" -pass 2 -passlogfile "$pl" -pix_fmt yuv420p -c:a aac -b:a "$5k" -movflags +faststart "$2"
  rm -f "$pl"*
}
for name in narrated music-only; do
  wa "$OUT/LeMSIC-advent-$name.mp4" "$OUT/LeMSIC-advent-$name-whatsapp.mp4" 720 720 96 &
  wa "$OUT/LeMSIC-advent-$name.mp4" "$OUT/LeMSIC-advent-$name-whatsapp-HD.mp4" 1080 2000 128 &
done
wait
step "done"
ls -l "$OUT"/LeMSIC-advent-*.mp4 | tee -a "$LOG"
