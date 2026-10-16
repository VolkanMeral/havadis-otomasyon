#!/usr/bin/env python3
"""Havadis videoları için ÖZGÜN arka plan müziği üretir (telif sorunu yok: tamamen kodla sentezlenir).
12 sn, 120 BPM, La minör: yumuşak pad + bas + hafif ritim, 5. sn'de sayfa geçişi için 'whoosh',
10. sn'de logo için kısa çan sesi. Kullanım: python muzik_uret.py [çıktı.wav] [süre]"""
import sys
import wave

import numpy as np

SR = 44100
CIKTI = sys.argv[1] if len(sys.argv) > 1 else "assets/muzik.wav"
SURE = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
GECIS, LOGO = SURE * 5 / 12, SURE - 2.0
BPM = 120
VURUS = 60 / BPM
rng = np.random.default_rng(7)
n = int(SURE * SR)
t = np.arange(n) / SR
mix = np.zeros((n, 2))


def hz(nota):  # MIDI nota -> frekans
    return 440 * 2 ** ((nota - 69) / 12)


def ekle(sinyal, bas_sn, kazanc=1.0, pan=0.0):
    i = int(bas_sn * SR)
    s = sinyal[: max(0, n - i)] * kazanc
    mix[i:i + len(s), 0] += s * (1 - pan) / 2 ** 0.5 * 1.41 / 2
    mix[i:i + len(s), 1] += s * (1 + pan) / 2 ** 0.5 * 1.41 / 2


def zarf(uzunluk, atak=0.01, birak=0.3):
    m = int(uzunluk * SR)
    e = np.ones(m)
    a, r = int(atak * SR), int(birak * SR)
    e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def lowpass(x, kesim):
    a = np.exp(-2 * np.pi * kesim / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


# Akorlar (her biri 2 sn = 1 ölçü): Am – F – C – G – Am – F
AKORLAR = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
OLCU = 4 * VURUS
for k, akor in enumerate(AKORLAR):
    bas = k * OLCU
    if bas >= SURE:
        break
    u = min(OLCU + 0.4, SURE - bas)
    tt = np.arange(int(u * SR)) / SR
    pad = sum(np.sin(2 * np.pi * hz(no) * tt * (1 + d)) for no in akor for d in (-0.003, 0.003))
    pad += 0.3 * sum(np.sin(2 * np.pi * 2 * hz(no) * tt) for no in akor)
    ekle(pad * zarf(u, 0.5, 0.6), bas, 0.035)
    # bas: her vuruşta kısa "pluck"
    for v in range(4):
        vb = bas + v * VURUS
        if vb >= SURE:
            break
        tb = np.arange(int(0.45 * SR)) / SR
        f = hz(akor[0] - 12)
        pl = (np.sin(2 * np.pi * f * tb) + 0.4 * np.sin(2 * np.pi * 2 * f * tb)) * np.exp(-tb * 7)
        ekle(pl, vb, 0.16 if v % 2 == 0 else 0.11)

# Ritim: yumuşak kick 1-3'te, hi-hat ara vuruşlarda (ilk ölçüde yok, yavaş giriş)
for v in range(int(SURE / VURUS) * 2):
    an = v * VURUS / 2
    if an < OLCU or an >= LOGO:
        continue
    if v % 4 == 0:
        tk = np.arange(int(0.3 * SR)) / SR
        kick = np.sin(2 * np.pi * (45 + 80 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 12)
        ekle(kick, an, 0.35)
    if v % 2 == 1:
        hh = rng.standard_normal(int(0.06 * SR))
        hh = (hh - lowpass(hh, 6000)) * np.exp(-np.arange(len(hh)) / SR * 70)
        ekle(hh, an, 0.05, pan=0.3)

# Sayfa geçişi: yükselen gürültü (whoosh)
wu = 0.9
w = rng.standard_normal(int(wu * SR))
kes = np.linspace(400, 5000, len(w))
wy = np.empty_like(w)
acc = 0.0
for i, v in enumerate(w):
    a = np.exp(-2 * np.pi * kes[i] / SR)
    acc = (1 - a) * v + a * acc
    wy[i] = acc
ekle(wy * np.sin(np.linspace(0, np.pi, len(w))) ** 2, GECIS - wu * 0.75, 0.25)

# Logo: kısa çan akoru (A – C# – E üst oktav), müzik altında kısılır
tc = np.arange(int(2.0 * SR)) / SR
can = sum(np.sin(2 * np.pi * hz(no) * tc) + 0.25 * np.sin(2 * np.pi * 2.76 * hz(no) * tc) for no in (81, 85, 88))
ekle(can * np.exp(-tc * 2.2), LOGO, 0.07)

# Logo sırasında arka plan kısılır, son 0,5 sn tamamen söner
son = np.ones(n)
i0, i1 = int((SURE - 0.6) * SR), n
son[i0:i1] = np.linspace(1, 0, i1 - i0)
mix *= son[:, None]
mix[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]
mix = np.tanh(mix * 1.2)  # hafif sıkıştırma
mix *= 0.5 / np.max(np.abs(mix))

with wave.open(CIKTI, "wb") as f:
    f.setnchannels(2)
    f.setsampwidth(2)
    f.setframerate(SR)
    f.writeframes((mix * 32767).astype("<i2").tobytes())
print("Müzik hazır:", CIKTI, f"({SURE:.0f} sn)")
