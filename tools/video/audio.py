"""The promo film's sound: Santa's narration, an original Christmas waltz, wind, fire and effects.

    python tools/video/audio.py

Reads build/video/out/cues.json (written by compose.py: when each line and effect happens) and
build/video/vo/*.wav (tools/video/narrate.py). Writes build/video/out/mix-voice.wav (narration,
music, ambience, effects) and mix-novoice.wav (the same without the narration), both 48 kHz stereo.
Needs numpy, scipy and soundfile, and ffmpeg (for the voice's pitch and tone).
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
B = os.path.join(ROOT, "build", "video")
SR = 48000
rng = np.random.default_rng(2412)
CUES = json.load(open(os.path.join(B, "out", "cues.json")))
TOTAL = CUES["total"] + 0.5
N = int(TOTAL * SR)
SCN = CUES["scenes"]


def buf():
    return np.zeros((N, 2), np.float32)


def add(dst, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    if sig.ndim == 1:
        l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    n = min(len(sig), N - i)
    dst[i:i + n] += sig[:n] * gain


def lowpass(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def highpass(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def reverb(x, seconds=2.4, wet=0.28, damp=5000):
    """A soft hall: convolve with a decaying, darkening stereo noise tail."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t * 6.9 / seconds)[:, None]
    ir = lowpass(ir, damp)
    ir[: int(0.012 * SR)] = 0
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    mono = x if x.ndim == 2 else np.stack([x, x], 1)
    wetsig = np.stack([fftconvolve(mono[:, c], ir[:, c])[: len(mono)] for c in range(2)], 1)
    return mono * (1 - wet) + wetsig * wet * 2.2


# ---------------------------------------------------------------- the instruments
def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def celesta(f, dur=2.2, amp=0.35):
    t = np.arange(int(dur * SR)) / SR
    idx = 1.6 * np.exp(-t * 6)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 4.0 * t))
    y += 0.25 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 4)
    env = np.exp(-t * 2.4) * np.minimum(1, t / 0.003)
    return (y * env * amp).astype(np.float32)


def musicbox(f, dur=1.4, amp=0.16):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * f * t + 0.8 * np.exp(-t * 9) * np.sin(2 * np.pi * f * 5.03 * t)) + 0.18 * np.sin(2 * np.pi * f * 3.99 * t) * np.exp(-t * 7)
    return (y * np.exp(-t * 3.6) * np.minimum(1, t / 0.002) * amp).astype(np.float32)


def pluck(f, dur=1.5, amp=0.32):
    t = np.arange(int(dur * SR)) / SR
    y = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) * np.exp(-t * 6)
    return (y * np.exp(-t * 3.2) * np.minimum(1, t / 0.006) * amp).astype(np.float32)


def pad(freqs, dur, amp=0.07, cutoff=1400):
    """Soft strings: detuned saws, made of harmonics, darker above the cutoff, slow in and out."""
    t = np.arange(int(dur * SR)) / SR
    y = np.zeros_like(t)
    for f in freqs:
        for det in (-0.004, 0.0, 0.0045):
            ff = f * (1 + det)
            for h in range(1, 16):
                if ff * h > 6000:
                    break
                y += np.sin(2 * np.pi * ff * h * t + rng.uniform(0, 6.3)) / h / (1 + (ff * h / cutoff) ** 2)
    att, rel = 0.7, 1.1
    env = np.minimum(1, t / att) * np.minimum(1, np.maximum(0, (dur - t) / rel))
    vib = 1 + 0.06 * np.sin(2 * np.pi * 0.25 * t)
    return (y * env * vib * amp / len(freqs)).astype(np.float32)


def sleigh(dur=0.25, amp=0.05):
    out = np.zeros(int(dur * SR), np.float32)
    for _ in range(9):
        f = rng.uniform(4500, 8500)
        t = np.arange(int(0.12 * SR)) / SR
        s = np.sin(2 * np.pi * f * t + 2 * np.sin(2 * np.pi * f * 1.41 * t)) * np.exp(-t * 38)
        i = int(rng.uniform(0, 0.05) * SR)
        out[i:i + len(s)] += s[: len(out) - i] * rng.uniform(0.4, 1)
    return out * amp


# ---------------------------------------------------------------- an original waltz in D, 84 beats a minute, 3/4
BEAT = 60 / 84
CHORDS = {"D": [50, 54, 57], "Bm": [47, 50, 54], "G": [43, 47, 50], "A": [45, 49, 52], "F#m": [42, 45, 49], "Em": [40, 43, 47],
          "A7": [45, 49, 52, 55]}
# 16 bars: (chord, melody notes as (midi, beats))
A4, B4, C5, D5, E5, F5, G5, A5 = 69, 71, 73, 74, 76, 78, 79, 81
FS4, G4, E4, D4 = 66, 67, 64, 62
PHRASE = [
    ("D", [(FS4, 1), (A4, 1), (D5, 1)]), ("Bm", [(C5, 2), (B4, 1)]), ("G", [(B4, 1), (A4, 1), (G4, 1)]), ("A", [(A4, 3)]),
    ("D", [(FS4, 1), (A4, 1), (D5, 1)]), ("F#m", [(E5, 2), (C5, 1)]), ("G", [(D5, 1), (B4, 1), (C5, 1)]), ("D", [(D5, 3)]),
    ("Bm", [(B4, 1), (D5, 1), (F5, 1)]), ("G", [(G5, 1), (F5, 1), (E5, 1)]), ("D", [(F5, 2), (D5, 1)]), ("A", [(E5, 3)]),
    ("Bm", [(D5, 1), (C5, 1), (B4, 1)]), ("G", [(B4, 1), (A4, 1), (G4, 1)]), ("Em", [(G4, 1), (FS4, 1), (E4, 1)]), ("D", [(D4, 3)]),
]


def section_level(t):
    """How full the arrangement is at time t: (pad, celesta, music box, bass, sleigh bells)."""
    def inside(s):
        return SCN[s]["start"] <= t < SCN[s]["start"] + SCN[s]["dur"]
    if inside("s1"):
        return (1.0, 0.9, 0.0, 0.5, 0.0)
    if inside("s2") or inside("s3"):
        return (0.9, 0.8, 0.8, 0.8, 0.0)
    if inside("s7"):
        k = (t - SCN["s7"]["start"]) / SCN["s7"]["dur"]
        return (1.0, 0.2 if k < 0.75 else 0.9, 0.0, 0.3, 0.0)
    return (1.0, 1.0, 0.8, 1.0, 0.7)


def music():
    L = buf()
    pads, mel, box, bass, bells = (np.zeros(N, np.float32) for _ in range(5))
    bar = 3 * BEAT
    nbars = int(TOTAL / bar) + 1
    end_bar = nbars - 1
    for b in range(nbars):
        t0 = b * bar
        chord, notes = PHRASE[b % len(PHRASE)] if b < end_bar else ("D", [(D5, 3)])
        lv = section_level(t0 + 0.1)
        cf = [midi(n) for n in CHORDS[chord]]
        p = pad([f * 2 for f in cf], bar + 1.2 if b < end_bar else 5.0, 0.08 * lv[0])
        i = int(t0 * SR)
        pads[i:i + len(p)] += p[: max(0, N - i)]
        bs = pluck(cf[0] / 2 if cf[0] > 90 else cf[0], 1.6, 0.3 * lv[3])
        bass[i:i + len(bs)] += bs[: max(0, N - i)]
        bs2 = pluck(cf[2] / 2, 1.0, 0.16 * lv[3])
        j = int((t0 + 2 * BEAT) * SR)
        bass[j:j + len(bs2)] += bs2[: max(0, N - j)]
        tb = t0
        for n, beats in notes:
            c = celesta(midi(n), 2.4 if beats >= 2 else 1.8, 0.3 * lv[1])
            j = int(tb * SR)
            mel[j:j + len(c)] += c[: max(0, N - j)]
            tb += beats * BEAT
        for e in range(6):                         # music-box eighths through the chord
            n = CHORDS[chord][e % len(CHORDS[chord])] + 24 + (12 if e in (2, 5) else 0)
            m = musicbox(midi(n), 1.2, 0.11 * lv[2])
            j = int((t0 + e * BEAT / 2) * SR)
            box[j:j + len(m)] += m[: max(0, N - j)]
        for e in range(3):
            if lv[4] > 0:
                s = sleigh(0.3, 0.05 * lv[4] * (1.0 if e == 0 else 0.6))
                j = int((t0 + e * BEAT) * SR)
                bells[j:j + len(s)] += s[: max(0, N - j)]
    st = lambda x, pan: np.stack([x * (1 - pan) ** 0.5, x * (1 + pan) ** 0.5], 1)
    mix = st(pads, 0) * 1.0 + st(mel, -0.15) + st(box, 0.35) * 0.9 + st(bass, 0) + st(bells, 0.25)
    mix = highpass(mix, 45)
    mix = reverb(mix, 2.8, 0.32)
    fade = np.ones(N, np.float32)
    fade[-int(2.5 * SR):] = np.linspace(1, 0, int(2.5 * SR))
    return (mix * fade[:, None]).astype(np.float32)


# ---------------------------------------------------------------- ambience and effects
def wind(seconds):
    n = int(seconds * SR)
    x = rng.normal(0, 1, (n, 2)).astype(np.float32)
    x = bandpass(x, 180, 1400)
    t = np.arange(n) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.11 * t + 1.0) * np.sin(2 * np.pi * 0.047 * t)
    return (x * gust[:, None] * 0.05).astype(np.float32)


def fire(seconds):
    n = int(seconds * SR)
    x = lowpass(rng.normal(0, 1, (n, 2)), 500) * 0.04
    for _ in range(int(seconds * 7)):
        i = int(rng.uniform(0, n - 3000))
        k = int(rng.uniform(80, 900))
        c = rng.normal(0, 1, k) * np.exp(-np.arange(k) / (k / 4))
        x[i:i + k] += (c * rng.uniform(0.04, 0.16))[:, None] * np.array([rng.uniform(0.5, 1), rng.uniform(0.5, 1)])
    return highpass(x, 60).astype(np.float32)


def sfx(name):
    t = lambda s: np.arange(int(s * SR)) / SR
    if name in ("tap", "click", "key"):
        tt = t(0.06)
        f = {"tap": 1800, "click": 2600, "key": 3200}[name]
        s = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 140) + rng.normal(0, 0.3, len(tt)) * np.exp(-tt * 300)
        return s * {"tap": 0.25, "click": 0.22, "key": 0.13}[name]
    if name == "tick":
        tt = t(0.05)
        return (bandpass(rng.normal(0, 1, len(tt)) * np.exp(-tt * 180), 1500, 5000) * 0.5)
    if name in ("door", "doorclose"):
        tt = t(1.2)
        creak = np.sin(2 * np.pi * (180 + 60 * np.sin(2 * np.pi * 3 * tt)) * tt) * np.exp(-tt * 1.5) * (tt < 0.9) * 0.05
        thump = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 18) * 0.5
        latch = np.concatenate([np.zeros(int(0.02 * SR)), rng.normal(0, 1, int(0.03 * SR)) * 0.2])
        s = (creak if name == "door" else thump) + (np.pad(latch, (0, len(tt) - len(latch))) if name == "door" else 0)
        return lowpass(s, 3000)
    if name == "whoosh":
        tt = t(1.0)
        s = rng.normal(0, 1, len(tt))
        env = np.sin(np.pi * np.clip(tt / 0.9, 0, 1)) ** 2
        return bandpass(s, 300, 3500) * env * 0.12
    if name == "spin":
        tt = t(0.8)
        return bandpass(rng.normal(0, 1, len(tt)), 400, 2500) * np.sin(np.pi * tt / 0.8) ** 2 * 0.08
    if name in ("chime", "tada"):
        notes = [74, 78, 81, 86, 90] if name == "chime" else [62, 69, 74, 78, 81, 86]
        out = np.zeros(int(2.6 * SR), np.float32)
        for k, n in enumerate(notes):
            c = celesta(midi(n), 2.2, 0.22)
            i = int(k * (0.06 if name == "chime" else 0.025) * SR)
            out[i:i + len(c)] += c[: len(out) - i]
        if name == "tada":
            out[: int(0.6 * SR)] += sleigh(0.6, 0.12)
        return out
    return np.zeros(10, np.float32)


def voice_track():
    """Each line lowered (formants kept), warmed and given a little room, then placed."""
    pitch = json.load(open(os.path.join(B, "vo", "timing.json")))["pitch"]
    out = buf()
    tmp = os.path.join(B, "out", "vo-processed")
    os.makedirs(tmp, exist_ok=True)
    for ln in CUES["lines"]:
        src = os.path.join(B, "vo", ln["name"] + ".wav")
        dst = os.path.join(tmp, ln["name"] + ".wav")
        chain = ("highpass=f=60,aresample=48000" if abs(pitch - 1.0) < 1e-3 else       # a real-sounding voice: as it is
                 f"rubberband=pitch={pitch}:formant=preserved,equalizer=f=130:t=q:w=1:g=3,"
                 "equalizer=f=3200:t=q:w=1.4:g=1.5,highshelf=f=9000:g=-3,aresample=48000")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-af", chain, "-ac", "2", dst], check=True)
        a, sr = sf.read(dst, dtype="float32")
        add(out, a, ln["at"])
    out = reverb(out, 1.1, 0.12 if abs(pitch - 1.0) > 1e-3 else 0.05, 4500)
    pk = np.abs(out).max()
    return out * (0.7 / pk) if pk > 0 else out


def main():
    S = CUES["scenes"]
    amb = buf()
    for sc in ("s1", "s8"):
        add(amb, wind(S[sc]["dur"] + 1), S[sc]["start"], 1.0)
    add(amb, wind(S["s3"]["dur"]), S["s3"]["start"], 0.8)
    inside = S["s4"]["start"] - 1.5
    add(amb, fire(S["s8"]["start"] + 2.5 - inside), inside, 0.55)
    fx = buf()
    for c in CUES["sfx"]:
        gain = {"tick": 0.5, "key": 0.9, "tada": 0.8, "chime": 0.7}.get(c["sfx"], 0.8)
        add(fx, sfx(c["sfx"]), c["at"], gain, pan=0.0)
    fx = reverb(fx, 1.4, 0.18)
    mus = music()
    vo = voice_track()
    env = np.abs(vo).mean(1)
    k = int(0.05 * SR)
    env = np.convolve(env, np.ones(k) / k, "same")
    sm = np.zeros_like(env)
    a_att, a_rel = np.exp(-1 / (0.05 * SR)), np.exp(-1 / (0.45 * SR))
    acc = 0.0
    for i in range(0, len(env), 64):                                            # envelope follower, 64-sample steps
        x = env[i]
        acc = x + (acc - x) * (a_att ** 64 if x > acc else a_rel ** 64)
        sm[i:i + 64] = acc
    duck = 1 - 0.62 * np.clip(sm / (np.percentile(sm[sm > 0], 90) + 1e-6), 0, 1)
    for name, with_vo in (("mix-voice.wav", True), ("mix-novoice.wav", False)):
        m = mus * (duck[:, None] if with_vo else 1.0) * 0.55 + amb * 0.9 + fx * 0.8 + (vo * 1.0 if with_vo else 0)
        path = os.path.join(B, "out", name)
        sf.write(path + ".tmp.wav", m.astype(np.float32), SR, subtype="FLOAT")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", path + ".tmp.wav",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", "48000", path], check=True)
        os.remove(path + ".tmp.wav")
        print("wrote", name)


if __name__ == "__main__":
    main()
