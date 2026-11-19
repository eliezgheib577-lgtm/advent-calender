"""The narration for the promo film, one WAV per line, in a deep, warm, Santa-like voice.

    python tools/video/narrate.py [voice: 1 jolly | 2 blend | 3 deep] [--speed=0.95]

Uses the open Kokoro voice model (pip install kokoro-onnx soundfile; the model files
kokoro-v1.0.onnx and voices-v1.0.bin from github.com/thewh1teagle/kokoro-onnx releases, in
build/video/tts/). The lines are in tools/video/narration.json ("LeMSIC" is spelt "Lemsick" there
so it's said right). Writes build/video/vo/<scene>-<n>.wav and timing.json; tools/video/audio.py
lowers and warms the voice when it mixes the film.
"""
import json
import os
import sys

import soundfile as sf
from kokoro_onnx import Kokoro

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TTS = os.path.join(ROOT, "build", "video", "tts")
OUT = os.path.join(ROOT, "build", "video", "vo")
args = [a for a in sys.argv[1:] if not a.startswith("--")]
choice = args[0] if args else "2"
speed = float(next((a.split("=")[1] for a in sys.argv if a.startswith("--speed=")), 0.95))
k = Kokoro(os.path.join(TTS, "kokoro-v1.0.onnx"), os.path.join(TTS, "voices-v1.0.bin"))
santa, mich = k.get_voice_style("am_santa"), k.get_voice_style("am_michael")
style = {"1": santa, "2": 0.5 * santa + 0.5 * mich, "3": mich}[choice]
PITCH = {"1": 0.84, "2": 0.87, "3": 0.9}[choice]
os.makedirs(OUT, exist_ok=True)
timing = {}
for scene, lines in json.load(open(os.path.join(HERE, "narration.json"))):
    for i, line in enumerate(lines):
        a, sr = k.create(line, voice=style, speed=speed, lang="en-us")
        sf.write(os.path.join(OUT, f"{scene}-{i}.wav"), a, sr)
        timing[f"{scene}-{i}"] = round(len(a) / sr, 3)
json.dump({"voice": choice, "speed": speed, "pitch": PITCH, "lines": timing}, open(os.path.join(OUT, "timing.json"), "w"), indent=1)
print("speech", round(sum(timing.values()), 1), "s in", len(timing), "lines")
