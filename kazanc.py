#!/usr/bin/env python3
"""Facebook içerik para kazanma: bu ayın günlük kazancı ve gönderi bazında kazanç (sadece okuma).
Sonuç: rapor/kazanc.json"""
import datetime as dt
import json
import os
import re

import havadis_bot as bot

T = bot.PAGE_TOKEN
simdi = dt.datetime.now(dt.timezone.utc)
ay_bas = simdi.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
sonuc = {"zaman": simdi.isoformat(timespec="seconds"), "hatalar": {}}


def al(yol, **p):
    p["access_token"] = T
    j = bot.HTTP.get(bot.graph(yol), params=p, timeout=60).json()
    if "error" in j:
        raise RuntimeError(j["error"].get("message", "")[:200])
    return j


# Sayfa geneli günlük kazanç
for metrik in ("content_monetization_earnings", "monetization_approximate_earnings"):
    try:
        j = al(f"{bot.PAGE_ID}/insights", metric=metrik, period="day",
               since=int(ay_bas.timestamp()), until=int(simdi.timestamp()))
        sonuc[metrik] = [{"gun": v["end_time"][:10], "deger": v.get("value")}
                         for d in j.get("data", []) for v in d.get("values", [])]
    except Exception as e:
        sonuc["hatalar"][metrik] = str(e)

# Gönderi bazında: bu ay paylaşılan Facebook gönderi / Reels kimlikleri
kayitlar = [k for k in json.load(open("posted.json")) if str(k.get("zaman", "")) >= ay_bas.strftime("%Y-%m-%d")]
gonderiler = []
for k in kayitlar:
    for alan in ("facebook", "facebook_reel"):
        if k.get(alan):
            gonderiler.append((alan, str(k[alan]), k["baslik"], k["zaman"]))
sonuc["gonderi_sayisi"] = len(gonderiler)
sonuc["gonderiler"] = []
for alan, kimlik, baslik, zaman in gonderiler:
    kayit = {"tur": alan, "baslik": baslik, "zaman": zaman}
    for metrik in ("content_monetization_earnings",):
        try:
            hedef = kimlik if alan == "facebook" else kimlik.split("_")[-1]
            j = al(f"{hedef}/insights", metric=metrik, period="lifetime")
            kayit[metrik] = [v.get("value") for d in j.get("data", []) for v in d.get("values", [])]
        except Exception as e:
            kayit[metrik + "_hata"] = str(e)[:120]
    sonuc["gonderiler"].append(kayit)

metin = json.dumps(sonuc, ensure_ascii=False, indent=1)
metin = re.sub(r"access_token=[A-Za-z0-9]+", "access_token=REDACTED", metin)
os.makedirs("rapor", exist_ok=True)
open("rapor/kazanc.json", "w", encoding="utf-8").write(metin)
print("gönderi:", len(gonderiler), "hatalar:", list(sonuc["hatalar"]))
