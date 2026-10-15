#!/usr/bin/env python3
"""SADECE ÖRNEK: Türkçe yapay sesli ve altyazılı haber videosu üretir. Hiçbir yerde paylaşım yapmaz.
Kullanım: python ses_ornek.py <piper_ses_modeli.onnx> <çıktı.mp4>"""
import datetime as dt
import os
import subprocess
import sys
import wave

import havadis_bot as bot
import video_uret

MODEL, CIKTI = sys.argv[1], sys.argv[2]
GECICI = os.path.join(bot.KOK, "cikti")
os.makedirs(GECICI, exist_ok=True)

# (seslendirilecek metin, ekranda görünecek altyazı) – sayılar sesli okunuşta yazıyla yazılır
CUMLELER = [
    ("Avusturya'da pelet fiyatları rekor kırdı.",
     "Avusturya'da pelet fiyatları rekor kırdı."),
    ("Fiyatlar bir yılda yüzde otuz beş artarak, ton başına dört yüz yirmi avroya çıktı.",
     "Fiyatlar bir yılda %35 artarak ton başına 420 Euro'ya çıktı."),
    ("Ortalama bir müstakil evin kışlık pelet faturası, yaklaşık iki bin dört yüz avroya ulaştı.",
     "Ortalama bir müstakil evin kışlık pelet faturası yaklaşık 2.400 Euro'ya ulaştı."),
    ("Haberin tamamı, havadis nokta at'de.",
     "Haberin tamamı havadis.at'de"),
]
BASLANGIC = 0.8   # ilk cümleden önce kısa sessizlik
ARA = 0.3         # cümleler arası sessizlik
EN_FAZLA_KELIME = 6


def seslendir(metin, yol):
    subprocess.run(["piper", "--model", MODEL, "--output_file", yol], input=metin.encode("utf-8"), check=True)
    with wave.open(yol) as w:
        return w.getnframes() / w.getframerate(), w.getframerate()


def parcala(metin, bas, son):
    """Altyazıyı en fazla 6 kelimelik parçalara böler, süreyi karakter sayısına göre dağıtır."""
    k = metin.split()
    parcalar = [" ".join(k[i:i + EN_FAZLA_KELIME]) for i in range(0, len(k), EN_FAZLA_KELIME)]
    toplam = sum(len(p) for p in parcalar)
    t, sonuc = bas, []
    for p in parcalar:
        d = (son - bas) * len(p) / toplam
        sonuc.append((round(t, 2), round(t + d, 2), p))
        t += d
    return sonuc


altyazi, dosyalar, t = [], [], BASLANGIC
for i, (okunus, yazi) in enumerate(CUMLELER):
    yol = os.path.join(GECICI, f"cumle{i}.wav")
    sure, hz = seslendir(okunus, yol)
    altyazi += parcala(yazi, t, t + sure)
    dosyalar.append((yol, t))
    t += sure + ARA

# Cümleleri doğru zamanlara yerleştirip tek ses dosyası yap
ses = os.path.join(GECICI, "ses.wav")
girdiler, filtre = [], []
for j, (yol, bas) in enumerate(dosyalar):
    girdiler += ["-i", yol]
    filtre.append(f"[{j}]adelay={int(bas * 1000)}|{int(bas * 1000)}[a{j}]")
filtre.append("".join(f"[a{j}]" for j in range(len(dosyalar))) + f"amix=inputs={len(dosyalar)}:normalize=0[out]")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *girdiler, "-filter_complex", ";".join(filtre),
                "-map", "[out]", "-ac", "2", "-ar", "44100", ses], check=True)

video_sure = max(10.0, t + 2.4)  # konuşma bitince 2 sn logo
haber = {"baslik": "Pelet Fiyatları Rekor Artışta: Bir Kışın Maliyeti 2.400 Euro", "link": "",
         "kategori": "Avusturya", "resim": "", "tarih": dt.datetime(2026, 10, 15),
         "ozet": "Avusturya'da pelet fiyatları bir yılda yüzde 35 artarak ton başına 420 Euroya yükseldi."}
ic = bot.basit_icerik(haber)
foto = open(os.path.join(bot.KOK, "ornek", "foto1.jpg"), "rb").read()
video_uret.video_uret(haber, ic, CIKTI, foto, ses=ses, altyazi=altyazi, sure=video_sure)
print("Örnek hazır:", CIKTI, f"({video_sure:.1f} sn)")
