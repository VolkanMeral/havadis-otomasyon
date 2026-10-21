#!/usr/bin/env python3
"""Elle hazırlanmış bir videoyu (ozel/<klasör>/) Instagram Reels, Facebook Reels ve YouTube Shorts'a paylaşır.
Klasörde: video.mp4, metin.txt, isteğe bağlı kapak.jpg ve youtube_baslik.txt. Sonuç: sonuc.json"""
import json
import os
import sys

import havadis_bot as bot

klasor = os.path.join("ozel", sys.argv[1])
platformlar = (sys.argv[2] if len(sys.argv) > 2 else "instagram,facebook,youtube").split(",")
video = os.path.join(klasor, "video.mp4")
metin = open(os.path.join(klasor, "metin.txt"), encoding="utf-8").read().strip()
kapak = os.path.join(klasor, "kapak.jpg")
kapak = kapak if os.path.exists(kapak) else None
yb = os.path.join(klasor, "youtube_baslik.txt")
yt_baslik = open(yb, encoding="utf-8").read().strip() if os.path.exists(yb) else metin.split("\n")[0]
sonuc, hata = {}, False
for p in platformlar:
    try:
        if p == "instagram":
            sonuc[p] = bot.instagram_video(video, "REELS", metin)
        elif p == "facebook":
            sonuc[p] = bot.facebook_reel(video, metin, kapak)
        elif p == "youtube":
            import youtube
            sonuc[p] = youtube.yukle(video, yt_baslik, metin, ["havadis", "Almanya", "Merz", "haber"])
        print(f"{p}: paylaşıldı ({sonuc[p]})")
    except Exception as e:
        hata = True
        sonuc[p] = f"HATA: {e}"
        print(f"::error title={p} paylaşım hatası::{e}")
json.dump(sonuc, open(os.path.join(klasor, "sonuc.json"), "w"), ensure_ascii=False, indent=1)
sys.exit(1 if hata else 0)
