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
_eski = os.path.join(klasor, "sonuc.json")
if os.path.exists(_eski):
    sonuc = {k: v for k, v in json.load(open(_eski)).items() if not str(v).startswith("HATA")}
for p in platformlar:
    try:
        if p == "instagram":
            try:
                ig_video = os.path.join(klasor, "video_ig.mp4")
                sonuc[p] = bot.instagram_video(ig_video if os.path.exists(ig_video) else video, "REELS", metin)
            except Exception as e:
                # Yedek yol: Facebook'a yüklenmiş aynı videonun adresiyle (video_url) paylaş
                eski = {}
                if os.path.exists(os.path.join(klasor, "sonuc.json")):
                    eski = json.load(open(os.path.join(klasor, "sonuc.json")))
                fb_id = sonuc.get("facebook") or eski.get("facebook")
                if not fb_id or str(fb_id).startswith("HATA"):
                    raise
                print("Instagram doğrudan yükleme başarısız, Facebook video adresiyle deneniyor:", e)
                src = bot.kontrol(bot.HTTP.get(bot.graph(str(fb_id)), timeout=60,
                                               params={"fields": "source", "access_token": bot.PAGE_TOKEN}))["source"]
                kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
                    "media_type": "REELS", "video_url": src, "caption": metin, "share_to_feed": "true",
                    "thumb_offset": "3000", "access_token": bot.PAGE_TOKEN}))
                bot.ig_bekle(kap["id"], deneme=90, aralik=5)
                sonuc[p] = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media_publish"), timeout=60,
                                       data={"creation_id": kap["id"], "access_token": bot.PAGE_TOKEN}))["id"]
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
