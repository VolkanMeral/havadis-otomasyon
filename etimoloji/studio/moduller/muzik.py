"""Özgün, kodla üretilen belgesel müziği (telifsiz). Hicaz renkli drone + pad + mızrap + vuruşlar."""
import numpy as np, wave, sys, json

SR = 44100

def adsr(n, a, r):
    e = np.ones(n)
    a = min(int(a * SR), n // 2); r = min(int(r * SR), n - a)
    e[:a] = np.linspace(0, 1, a); e[n - r:] = np.linspace(1, 0, r) ** 2
    return e

def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)

def pad(freqs, dur, vol):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        for det in (-0.12, 0.0, 0.11):
            ff = f * 2 ** (det / 12)
            s += np.sin(2 * np.pi * ff * t + np.random.rand() * 6) * 0.6
            s += np.sin(2 * np.pi * ff * 2 * t) * 0.12
    lfo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    return s * adsr(n, dur * 0.35, dur * 0.45) * lfo * vol / len(freqs)

def pluck(f, dur, vol):
    n = int(dur * SR); p = max(2, int(SR / f))
    buf = np.random.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return out * vol * adsr(n, 0.002, dur * 0.4)

def boom(dur, vol, f0=55):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f0 * (1 + 1.5 * np.exp(-t * 18))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 2.2) * vol

def wind(dur, vol):
    n = int(dur * SR); w = np.random.randn(n)
    k = int(SR * 0.004); w = np.convolve(w, np.ones(k) / k, mode="same")
    t = np.arange(n) / SR
    return w * vol * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t + 1))

def put(mix, sig, at):
    i = int(at * SR); j = min(len(mix), i + len(sig)); mix[i:j] += sig[: j - i]

def uret(sure, vurgu_anlari, cikis):
    np.random.seed(7)
    n = int(sure * SR); L = np.zeros(n); R = np.zeros(n)
    t = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * hz(38) * t) * 0.5 + np.sin(2 * np.pi * hz(45) * t) * 0.3)
    drone *= np.clip(t / 3, 0, 1) * np.clip((sure - t) / 2.5, 0, 1) * 0.16
    L += drone; R += drone
    w = wind(sure, 0.05); L += w; R += np.roll(w, 900)
    akorlar = [[62, 65, 69], [58, 62, 65], [55, 58, 62], [57, 61, 64]]  # Dm Bb Gm A
    seg = 6.8; k = 0
    while k * seg < sure - 1:
        p = pad([hz(m) for m in akorlar[k % 4]], seg + 2.5, 0.20)
        put(L, p, k * seg); put(R, np.roll(p, 400), k * seg); k += 1
    hicaz = [62, 63, 66, 67, 69, 70, 72, 74]
    motif = [0, 1, 2, 1, 0, 4, 3, 2, 1, 0]
    tt = 12.2; i = 0
    while tt < sure - 6:
        if not (44.8 < tt < 47.2):
            m = hicaz[motif[i % len(motif)]] + (12 if (i // 10) % 2 else 0)
            pl = pluck(hz(m), 1.6, 0.22)
            pan = 0.35 + 0.3 * np.sin(i)
            put(L, pl * (1 - pan), tt); put(R, pl * pan, tt)
        tt += 0.86 if i % 5 != 4 else 1.72; i += 1
    for a in vurgu_anlari:
        b = boom(2.5, 0.55); put(L, b, a); put(R, b, a)
    # final: derin açılış akoru
    son = pad([hz(50), hz(57), hz(62), hz(65)], 8.5, 0.34)
    put(L, son, sure - 8.2); put(R, son, sure - 8.2)
    b = boom(4.0, 0.8, 45); put(L, b, sure - 7.6); put(R, b, sure - 7.6)
    st = np.stack([L, R], 1)
    st /= np.max(np.abs(st)) / 0.85
    fade = int(SR * 1.2); st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    with wave.open(cikis, "wb") as f:
        f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes((st * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    sen = json.load(open(sys.argv[1]))
    vurgu = [s["bas"] for s in sen["sahneler"] if s["id"] in ("kok", "rivayet", "yolculuk")]
    uret(sen["sure"], vurgu, sys.argv[2])
