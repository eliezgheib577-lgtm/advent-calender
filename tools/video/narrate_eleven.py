"""The film's narration with an ElevenLabs voice (realistic), one WAV per line.

    python3 tools/video/narrate_eleven.py [voice_id] [model]

Defaults: Bill (pqHfZKP75CvOlQylNhV4) on eleven_v3, with a few delivery cues in [brackets] that the
v3 model performs rather than reads. The API key comes from the environment's network secrets for
api.elevenlabs.io (the proxy adds it), so nothing here holds it. Writes build/video/vo/<scene>-<n>.wav
and timing.json (pitch 1.0: the voice is used as it is). Lines are in tools/video/narration.json.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "build", "video", "vo")
RAW = os.path.join(ROOT, "build", "video", "eleven", "lines")
VOICE = sys.argv[1] if len(sys.argv) > 1 else "pqHfZKP75CvOlQylNhV4"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "eleven_v3"
CUES = {   # how Santa says some lines (eleven_v3 audio tags)
    "s1-0": "[warmly]", "s1-2": "[excited]", "s2-0": "[cheerfully]", "s2-2": "[playfully]", "s3-0": "[warmly]",
    "s3-1": "[reassuringly]", "s4-0": "[warmly]", "s4-2": "[mysteriously]", "s5-2": "[delighted]", "s6-1": "[warmly]",
    "s7-0": "[chuckles]", "s7-2": "[excited]", "s8-0": "[warmly]", "s8-3": "[joyfully]",
}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)
    timing = {}
    for scene, lines in json.load(open(os.path.join(HERE, "narration.json"))):
        for i, line in enumerate(lines):
            name = f"{scene}-{i}"
            text = (CUES.get(name, "") + " " + line).strip() if MODEL == "eleven_v3" else line
            body = {"text": text, "model_id": MODEL}
            body["voice_settings"] = {"stability": 0.5} if MODEL == "eleven_v3" else \
                {"stability": 0.42, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}
            mp3 = os.path.join(RAW, name + ".mp3")
            if not os.path.exists(mp3):
                r = subprocess.run(["curl", "-sS", "-m", "120", "-o", mp3, "-w", "%{http_code}",
                                    f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
                                    "-H", "xi-api-key: proxy-injected", "-H", "Content-Type: application/json",
                                    "-d", json.dumps(body)], capture_output=True, text=True)
                if r.stdout != "200":
                    msg = open(mp3).read()[:300] if os.path.exists(mp3) else r.stderr
                    os.remove(mp3) if os.path.exists(mp3) else None
                    sys.exit(f"{name}: HTTP {r.stdout} {msg}")
            wav = os.path.join(OUT, name + ".wav")      # trimmed of the silence at either end
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", mp3, "-af",
                            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
                            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.12,areverse",
                            "-ar", "44100", "-ac", "1", wav], check=True)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                                       capture_output=True, text=True).stdout)
            timing[name] = round(dur, 3)
            print(name, timing[name], "s", flush=True)
    json.dump({"voice": f"elevenlabs:{VOICE}:{MODEL}", "pitch": 1.0, "lines": timing}, open(os.path.join(OUT, "timing.json"), "w"), indent=1)
    print("speech", round(sum(timing.values()), 1), "s in", len(timing), "lines")


if __name__ == "__main__":
    main()
