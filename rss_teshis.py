#!/usr/bin/env python3
"""RSS erişim teşhisi: farklı adres ve başlıklarla durum kodunu yazar (paylaşım yapmaz)."""
import requests
UA_BOT = "HavadisSosyalMedyaBot/1.0 (+https://havadis.at)"
UA_TAR = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
for adres in ("https://havadis.at/rss.rss", "https://www.havadis.at/rss.rss", "https://havadis.at/", "https://www.havadis.at/haber/lochauda-genis-capli-polis-operasyonu-h57106.html"):
    for ad, bas in (("bot", {"User-Agent": UA_BOT}), ("tarayici", {"User-Agent": UA_TAR}),
                    ("tarayici+accept", {"User-Agent": UA_TAR, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                         "Accept-Language": "de-AT,de;q=0.9,tr;q=0.8"}),
                    ("curl", {"User-Agent": "curl/8.5.0", "Accept": "*/*"})):
        try:
            r = requests.get(adres, headers=bas, timeout=30)
            govde = r.text[:120].replace("\n", " ")
            print(f"::warning title={adres} [{ad}]::{r.status_code} item={'<item' in r.text} {r.headers.get('server','')} | {govde}")
        except Exception as e:
            print(f"::warning title={adres} [{ad}]::HATA {e}")

# Botun kendi oturumuyla aynı istek
import os, time
os.environ.setdefault("DRY_RUN", "1")
import havadis_bot as bot
for i in range(3):
    r = bot.HTTP.get(bot.RSS_URL, timeout=30)
    print(f"::error title=BOT oturumu deneme {i}::{r.status_code} item={'<item' in r.text} istek-başlıkları={dict(r.request.headers)}")
    time.sleep(3)
