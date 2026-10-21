#!/usr/bin/env python3
"""Instagram Reels işleme testi: kapsayıcı oluşturur, işlenip işlenmediğine bakar, YAYINLAMAZ."""
import sys
import havadis_bot as bot
for video in sys.argv[1:]:
    try:
        kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
            "media_type": "REELS", "upload_type": "resumable", "access_token": bot.PAGE_TOKEN}))
        adres = kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{bot.GRAPH_VERSION}/{kap['id']}"
        bot._yukle(adres, video)
        bot.ig_bekle(kap["id"], deneme=60, aralik=5)
        print(f"{video}: İŞLENDİ (yayınlanmadı)")
    except Exception as e:
        print(f"::warning title={video}::{e}")
