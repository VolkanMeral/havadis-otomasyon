"""Müzik v2 – sinematik yaylı + piyano + ney benzeri nefesli. Özgün, kodla üretilir (telifsiz).
Seslendirme altına yerleşecek şekilde orta frekanslar sakin tutulur."""
import numpy as np, wave, sys, json
SR = 44100
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def env(n, a, r):
    e = np.ones(n); a = min(int(a * SR), n // 2); r = min(int(r * SR), n - a)
    e[:a] = np.linspace(0, 1, a) ** 1.5; e[n - r:] *= np.linspace(1, 0, r) ** 2; return e

def lowpass(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode="same")

def strings(notes, dur, vol):
    n = int(dur * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for m in notes:
        for det in (-0.08, 0.0, 0.07, 0.15):
            f = hz(m) * 2 ** (det / 12) * (1 + 0.003 * np.sin(2 * np.pi * 5.2 * t + det * 40))
            ph = 2 * np.pi * np.cumsum(f) / SR
            saw = 2 * ((ph / (2 * np.pi)) % 1) - 1
            s += saw
    s = lowpass(lowpass(s, 22), 14)
    return s * env(n, dur * 0.4, dur * 0.5) * vol / len(notes)

def piano(m, dur, vol):
    n = int(dur * SR); t = np.arange(n) / SR; f = hz(m)
    s = sum(np.sin(2 * np.pi * f * k * t) * (0.6 / k ** 1.3) * np.exp(-t * (1.6 + k * 0.9)) for k in range(1, 7))
    return s * vol * env(n, 0.004, 0.3)

def ney(m, dur, vol):
    n = int(dur * SR); t = np.arange(n) / SR
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.0 * t) * np.clip(t / 0.6, 0, 1)
    ph = 2 * np.pi * np.cumsum(hz(m) * vib) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)
    breath = lowpass(np.random.randn(n), 6) * 0.35
    return (tone + breath * (0.6 + 0.4 * np.sin(ph))) * vol * env(n, 0.35, dur * 0.45)

def taiko(vol, dur=2.2):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 62 * (1 + 0.8 * np.exp(-t * 25))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.0)
    hit = lowpass(np.random.randn(n), 3) * np.exp(-t * 40) * 0.4
    return (body + hit) * vol

def riser(dur, vol):
    n = int(dur * SR); t = np.arange(n) / SR
    s = lowpass(np.random.randn(n), 4) * (t / dur) ** 2.5
    return s * vol

def put(mix, sig, at, pan=0.5):
    i = int(at * SR); j = min(len(mix), i + len(sig))
    if j > i: mix[i:j, 0] += sig[: j - i] * (1 - pan) * 2 * 0.5 + sig[: j - i] * 0.25; mix[i:j, 1] += sig[: j - i] * pan * 2 * 0.5 + sig[: j - i] * 0.25

def uret(sure, vurgu, final_at, cikis):
    np.random.seed(21)
    mix = np.zeros((int(sure * SR), 2))
    # Akor dizisi (Re minör, Andalusian'dan kaçınan sakin dizi): Dm – F – C – Bb (her biri 4.6 sn)
    akor = [[50, 57, 62, 65], [53, 60, 65, 69], [48, 55, 60, 64], [46, 53, 58, 62]]
    seg = 4.6; k = 0
    while k * seg < sure - 4:
        st = strings(akor[k % 4], seg + 1.6, 0.30 if k > 0 else 0.22)
        put(mix, st, k * seg, 0.45 + 0.1 * (k % 2)); k += 1
    # Piyano: yumuşak arpej (ara sahnelerde)
    arp = [62, 69, 74, 77, 74, 69]
    t = 4.6; i = 0
    while t < final_at - 1:
        base = akor[int(t // seg) % 4]
        m = [base[1] + 12, base[2] + 12, base[3] + 12, base[2] + 12][i % 4]
        put(mix, piano(m, 2.4, 0.16), t, 0.62); t += 0.66; i += 1
    # Ney cümlesi: giriş ve rivayet sahnesinde
    for at, cumle in [(0.6, [(69, 1.6), (70, 0.8), (69, 1.8)]), (30.4, [(74, 1.4), (72, 0.7), (70, 0.7), (69, 2.6)])]:
        tt = at
        for m, d in cumle: put(mix, ney(m, d + 0.4, 0.20), tt, 0.38); tt += d
    for a in vurgu:
        put(mix, riser(1.4, 0.10), a - 1.4); put(mix, taiko(0.55), a)
    # Final: büyük açılış (D majör – Picardy) + taiko
    put(mix, riser(2.2, 0.14), final_at - 2.2)
    son = strings([38, 50, 57, 62, 66, 69], sure - final_at + 0.5, 0.55)
    put(mix, son, final_at); put(mix, taiko(0.8, 3.5), final_at)
    put(mix, piano(74, 4, 0.22), final_at + 0.1); put(mix, piano(78, 4, 0.16), final_at + 0.1)
    mix /= np.max(np.abs(mix)) / 0.88
    f = int(SR * 1.5); mix[-f:] *= np.linspace(1, 0, f)[:, None]
    f0 = int(SR * 0.4); mix[:f0] *= np.linspace(0, 1, f0)[:, None]
    with wave.open(cikis, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    sen = json.load(open(sys.argv[1]))
    S = {s["id"]: s for s in sen["sahneler"]}
    vurgu = [S["kok"]["bas"], S["rivayet"]["bas"], S["yolculuk"]["bas"]]
    uret(sen["sure"], vurgu, S["kapanis"]["buyuk"][0]["t"], sys.argv[2])
