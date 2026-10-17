#!/usr/bin/env python3
"""Havadis videoları için ÖZGÜN arka plan müziği üretir (telif sorunu yok: tamamen kodla sentezlenir).
120 BPM, La minör: yumuşak pad + bas + hafif ritim, sayfa geçişlerinde 'whoosh', son 2 sn'de kalın kapanış.
Kullanım: python muzik_uret.py [çıktı.wav] [süre]
Kod içinden: uret("muzik.wav", sure=85, gecisler=[4.0, 16.5, ...])  # uzun videolar için"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 120
VURUS = 60 / BPM
OLCU = 4 * VURUS
# Akorlar (her biri 1 ölçü = 2 sn): Am – F – C – G – Am – F, uzun parçalarda döngü
AKORLAR = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]]


def hz(nota):  # MIDI nota -> frekans
    return 440 * 2 ** ((nota - 69) / 12)


def zarf(uzunluk, atak=0.01, birak=0.3):
    m = int(uzunluk * SR)
    e = np.ones(m)
    a, r = min(int(atak * SR), m), min(int(birak * SR), m)
    if a:
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


def uret(cikti, sure=12.0, gecisler=None):
    """sure: parça uzunluğu (sn). gecisler: whoosh çalınacak sayfa geçişi anları (sn);
    verilmezse 12 sn'lik haber videosundaki gibi sürenin 5/12'si."""
    rng = np.random.default_rng(7)
    n = int(sure * SR)
    mix = np.zeros((n, 2))
    logo = sure - 2.0
    gecisler = [sure * 5 / 12] if gecisler is None else list(gecisler)

    def ekle(sinyal, bas_sn, kazanc=1.0, pan=0.0):
        i = int(bas_sn * SR)
        if i >= n:
            return
        s = sinyal[: n - i] * kazanc
        mix[i:i + len(s), 0] += s * (1 - pan) / 2
        mix[i:i + len(s), 1] += s * (1 + pan) / 2

    olcu_sayisi = int(np.ceil(sure / OLCU))
    for k in range(olcu_sayisi):
        akor = AKORLAR[k % len(AKORLAR)]
        bas = k * OLCU
        u = min(OLCU + 0.4, sure - bas)
        if u <= 0.05:
            break
        tt = np.arange(int(u * SR)) / SR
        pad = sum(np.sin(2 * np.pi * hz(no) * tt * (1 + d)) for no in akor for d in (-0.003, 0.003))
        pad += 0.3 * sum(np.sin(2 * np.pi * 2 * hz(no) * tt) for no in akor)
        ekle(pad * zarf(u, 0.5, 0.6), bas, 0.035)
        for v in range(4):  # bas: her vuruşta kısa "pluck"
            vb = bas + v * VURUS
            if vb >= sure:
                break
            tb = np.arange(int(0.45 * SR)) / SR
            f = hz(akor[0] - 12)
            pl = (np.sin(2 * np.pi * f * tb) + 0.4 * np.sin(2 * np.pi * 2 * f * tb)) * np.exp(-tb * 7)
            ekle(pl, vb, (0.16 if v % 2 == 0 else 0.11))

    # Ritim: yumuşak kick 1-3'te, hi-hat ara vuruşlarda (ilk ölçüde yok, yavaş giriş)
    for v in range(int(sure / VURUS) * 2):
        an = v * VURUS / 2
        if an < OLCU or an >= logo:
            continue
        if v % 4 == 0:
            tk = np.arange(int(0.3 * SR)) / SR
            ekle(np.sin(2 * np.pi * (45 + 80 * np.exp(-tk * 30)) * tk) * np.exp(-tk * 12), an, 0.35)
        if v % 2 == 1:
            hh = rng.standard_normal(int(0.06 * SR))
            hh = (hh - lowpass(hh, 6000)) * np.exp(-np.arange(len(hh)) / SR * 70)
            ekle(hh, an, 0.05, pan=0.3)

    # Sayfa geçişleri: yükselen gürültü (whoosh)
    wu = 0.9
    for g in gecisler:
        w = rng.standard_normal(int(wu * SR))
        kes = np.linspace(400, 5000, len(w))
        wy, acc = np.empty_like(w), 0.0
        for i, v in enumerate(w):
            a = np.exp(-2 * np.pi * kes[i] / SR)
            acc = (1 - a) * v + a * acc
            wy[i] = acc
        ekle(wy * np.sin(np.linspace(0, np.pi, len(w))) ** 2, max(0.0, g - wu * 0.75), 0.25)

    # Logo: kalın, dolgun kapanış – alçak "boom" + derin La majör akor + hafif çan parıltısı
    tc = np.arange(int(2.0 * SR)) / SR
    ekle(np.sin(2 * np.pi * (38 + 60 * np.exp(-tc * 18)) * tc) * np.exp(-tc * 3.0), logo, 0.55)
    akor = sum(np.sin(2 * np.pi * hz(no) * tc) + 0.5 * np.sin(2 * np.pi * 2 * hz(no) * tc)
               + 0.2 * np.sin(2 * np.pi * 3 * hz(no) * tc) for no in (45, 57, 61, 64))
    ekle(akor * np.exp(-tc * 1.6) * (1 - np.exp(-tc * 60)), logo, 0.09)
    ekle(sum(np.sin(2 * np.pi * hz(no) * tc) for no in (69, 76)) * np.exp(-tc * 3.0), logo, 0.03)

    # Son 0,6 sn söner, baştaki 0,3 sn yumuşak giriş
    son = np.ones(n)
    i0 = int((sure - 0.6) * SR)
    son[i0:] = np.linspace(1, 0, n - i0)
    mix *= son[:, None]
    mix[: int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]
    mix = np.tanh(mix * 1.2)  # hafif sıkıştırma
    mix *= 0.5 / np.max(np.abs(mix))

    with wave.open(cikti, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((mix * 32767).astype("<i2").tobytes())
    return cikti


if __name__ == "__main__":
    yol = sys.argv[1] if len(sys.argv) > 1 else "assets/muzik.wav"
    s = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    uret(yol, s)
    print("Müzik hazır:", yol, f"({s:.0f} sn)")
