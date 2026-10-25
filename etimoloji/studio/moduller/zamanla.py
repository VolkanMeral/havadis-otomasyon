"""Seslendirme parçalarının sürelerine göre senaryoyu yeniden zamanlar ve anlatım izini üretir.
Kullanım: zamanla.py senaryo.json anlatim.json ses_klasoru cikti_senaryo.json cikti_anlatim.wav"""
import json, sys, subprocess, copy
import numpy as np, wave

SR = 44100
_c = {}
def oku(yol):
    if yol not in _c:
        raw = subprocess.check_output(["ffmpeg", "-loglevel", "error", "-i", yol, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"])
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        e = np.convolve(np.abs(x), np.ones(441) / 441, mode="same"); thr = 0.02 * e.max()
        idx = np.where(e > thr)[0]
        a = max(0, idx[0] - int(0.06 * SR)); b = min(len(x), idx[-1] + int(0.12 * SR))
        _c[yol] = x[a:b]
    return _c[yol]
def sure(yol): return len(oku(yol)) / SR

sen = json.load(open(sys.argv[1])); an = json.load(open(sys.argv[2])); klasor = sys.argv[3]
yeni = copy.deepcopy(sen)
GIRIS, ARA = 0.30, 0.28
KUYRUK = {"giris": 0.5, "gizem": 1.0, "kok": 0.9, "anlam": 0.8, "rivayet": 0.8, "yolculuk": 0.9, "kapanis": 2.6, "kunye": 1.6}
EN_AZ = {"kunye": 4.5, "gizem": 6.0}
t = 0.0; seg_list = []
for sahne, eski in zip(yeni["sahneler"], sen["sahneler"]):
    parc = [p for p in an["parcalar"] if p["sahne"] == sahne["id"]]
    bas = t; c = bas + (0.25 if sahne["id"] == "giris" else GIRIS); alt = []
    for p in parc:
        d = sure(f"{klasor}/{p['id']}.mp3")
        alt.append({"t": round(c, 3), "metin": p.get("ekran", p["metin"]).replace("...", "…"), "sure": round(d, 3), "id": p["id"]})
        seg_list.append((c, f"{klasor}/{p['id']}.mp3")); c += d + ARA
    son = max(c - ARA + KUYRUK.get(sahne["id"], 0.8), bas + EN_AZ.get(sahne["id"], 0))
    olcek = (son - bas) / (eski["son"] - eski["bas"])
    for b in sahne.get("buyuk", []): b["t"] = round(bas + (b["t"] - eski["bas"]) * olcek, 3)
    for z in sahne.get("zincir", []): z["t"] = round(bas + (z["t"] - eski["bas"]) * olcek, 3)
    # anlatımla eşleşen vurgular (sahnedeki cümle sırasına göre)
    ts = [x["t"] for x in alt]
    if sahne["id"] == "kok" and len(ts) > 1:
        for b in sahne["buyuk"]:
            if b["stil"] == "kok_ar": b["t"] = ts[1]
            if b["stil"] == "kok_tr": b["t"] = ts[1] + 0.8
            if b["stil"] == "uyari_alt": b["t"] = ts[-1] + 0.6
    if sahne.get("zincir") and alt:
        b0 = alt[0]["t"]; b1 = alt[-1]["t"] + alt[-1]["sure"] * 0.8; n = len(sahne["zincir"])
        for i, z in enumerate(sahne["zincir"]): z["t"] = round(b0 + (b1 - b0) * i / max(1, n - 1) * 0.9, 3)
    if sahne["id"] == "rivayet" and ts:
        for b in sahne["buyuk"]:
            if b["stil"] == "uyari": b["t"] = ts[-1] + 1.0
    if sahne["id"] == "kapanis" and ts:
        sahne["buyuk"][0]["t"] = ts[-1] - 0.15
        sade = lambda x: "".join(ch for ch in x.lower() if ch.isalnum())
        if sade(sahne["buyuk"][0]["metin"]) == sade(alt[-1]["metin"]): alt = alt[:-1]  # aynı cümle büyük yazıyla ekranda
    if sahne["id"] == "kunye": alt = []
    sahne["altyazi"] = alt; sahne["bas"] = round(bas, 3); sahne["son"] = round(son, 3); t = son
yeni["sure"] = round(t, 3)
json.dump(yeni, open(sys.argv[4], "w"), ensure_ascii=False, indent=1)

iz = np.zeros(int((t + 1) * SR), np.float32)
for at, yol in seg_list:
    s = oku(yol); i = int(at * SR); iz[i:i + len(s)] += s
iz = iz[: int(t * SR)]; iz /= max(1e-6, np.max(np.abs(iz))) / 0.9
with wave.open(sys.argv[5], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((iz * 32767).astype(np.int16).tobytes())
print("toplam süre", round(t, 2))
