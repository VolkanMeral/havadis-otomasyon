#!/usr/bin/env python3
"""Instagram Reels işleme testi: kapsayıcı oluşturur, işlenip işlenmediğine bakar, YAYINLAMAZ."""
import sys
import os
import havadis_bot as bot


def parcali_yukle(adres, dosya, parca=4 * 1024 * 1024):
    boyut = os.path.getsize(dosya)
    with open(dosya, "rb") as f:
        ofs = 0
        while ofs < boyut:
            veri = f.read(parca)
            r = bot.HTTP.post(adres, data=veri, timeout=300, headers={
                "Authorization": f"OAuth {bot.PAGE_TOKEN}", "offset": str(ofs), "file_size": str(boyut)})
            print("parça", ofs, r.status_code, r.text[:150])
            bot.kontrol(r)
            ofs += len(veri)
for video in sys.argv[1:]:
    try:
        kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
            "media_type": "REELS", "upload_type": "resumable", "access_token": bot.PAGE_TOKEN}))
        adres = kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{bot.GRAPH_VERSION}/{kap['id']}"
        parcali_yukle(adres, video)
        bot.ig_bekle(kap["id"], deneme=60, aralik=5)
        print(f"{video}: İŞLENDİ (yayınlanmadı)")
    except Exception as e:
        print(f"::warning title={video}::{e}")
