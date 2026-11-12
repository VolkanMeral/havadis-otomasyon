#!/usr/bin/env python3
"""Otomatik sisteme geçişten önce ve sonra: günlük erişim, beğeni, yorum, takipçi (sadece okuma).
Sonuç: rapor/karsilastirma.json  (GUN_SAYISI gün geriye bakar, varsayılan 45)"""
import datetime as dt
import json
import os

import havadis_bot as bot

G = bot.graph
TOKEN = bot.PAGE_TOKEN
GUN = int(os.getenv("GUN_SAYISI", "45"))
simdi = dt.datetime.now(dt.timezone.utc)
bas = simdi - dt.timedelta(days=GUN)
hatalar = {}


def al(yol, **p):
    p["access_token"] = TOKEN
    r = bot.HTTP.get(yol if yol.startswith("http") else G(yol), params=p, timeout=60)
    j = r.json()
    if "error" in j:
        raise RuntimeError(j["error"].get("message", str(j["error"]))[:200])
    return j


def dene(ad, f):
    try:
        return f()
    except Exception as e:
        hatalar.setdefault(ad, str(e)[:200])
        return None


def sayfalar(yol, durdur, **p):
    """Sayfalı listeyi durdur(öğe) True olana kadar okur."""
    sonuc, j = [], al(yol, **p)
    while True:
        for x in j.get("data", []):
            if durdur(x):
                return sonuc
            sonuc.append(x)
        sonraki = j.get("paging", {}).get("next")
        if not sonraki or len(sonuc) > 3000:
            return sonuc
        r = bot.HTTP.get(sonraki, timeout=60).json()
        if "error" in r:
            raise RuntimeError(r["error"].get("message", "")[:200])
        j = r


def eski(zaman_alani):
    return lambda x: dt.datetime.fromisoformat(x[zaman_alani].replace("+0000", "+00:00")) < bas


def zaman_serisi(ad, obje, metrik, **ek):
    """period=day zaman serisi, 30 günlük parçalarla."""
    tum = {}
    a = bas
    while a < simdi:
        b = min(a + dt.timedelta(days=29), simdi)
        j = dene(f"{ad}", lambda: al(f"{obje}/insights", metric=metrik, period="day",
                                     since=int(a.timestamp()), until=int(b.timestamp()), **ek))
        for d in (j or {}).get("data", []):
            for v in d.get("values", []):
                tum[v["end_time"][:10]] = v.get("value")
        a = b
    return tum


def gunluk_toplam(ad, obje, metrik):
    """metric_type=total_value metrikleri için gün gün toplam (Instagram)."""
    tum = {}
    for i in range(GUN):
        g = (bas + dt.timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        j = dene(ad, lambda: al(f"{obje}/insights", metric=metrik, period="day", metric_type="total_value",
                                 since=int(g.timestamp()), until=int((g + dt.timedelta(days=1)).timestamp())))
        if j is None:
            break
        tum[g.date().isoformat()] = {d["name"]: d.get("total_value", {}).get("value") for d in j.get("data", [])}
    return tum


sonuc = {"zaman": simdi.isoformat(timespec="seconds"), "gun": GUN}

# ---- Instagram
sonuc["ig_medya"] = dene("ig_medya", lambda: [
    {k: m.get(k) for k in ("timestamp", "media_product_type", "media_type", "like_count", "comments_count")}
    for m in sayfalar(f"{bot.IG_USER_ID}/media", eski("timestamp"), limit=100,
                      fields="timestamp,media_product_type,media_type,like_count,comments_count")])
sonuc["ig_erisim"] = zaman_serisi("ig_reach", bot.IG_USER_ID, "reach")
sonuc["ig_takipci"] = zaman_serisi("ig_follower_count", bot.IG_USER_ID, "follower_count")
sonuc["ig_gunluk"] = gunluk_toplam("ig_total_value", bot.IG_USER_ID,
                                   "views,profile_views,website_clicks,accounts_engaged,total_interactions,likes")

# ---- Facebook
sonuc["fb_gonderi"] = dene("fb_gonderi", lambda: [
    {"zaman": p.get("created_time"), "tepki": p.get("reactions", {}).get("summary", {}).get("total_count"),
     "yorum": p.get("comments", {}).get("summary", {}).get("total_count"), "paylasim": p.get("shares", {}).get("count", 0)}
    for p in sayfalar(f"{bot.PAGE_ID}/posts", eski("created_time"), limit=100,
                      fields="created_time,shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)")])
sonuc["fb_sayfa"] = {}
for metrik in ("page_impressions_unique", "page_media_view", "page_views_total", "page_post_engagements",
               "page_daily_follows_unique", "page_follows", "page_total_media_view_unique"):
    s = zaman_serisi(f"fb_{metrik}", bot.PAGE_ID, metrik)
    if s:
        sonuc["fb_sayfa"][metrik] = s

sonuc["hatalar"] = hatalar
os.makedirs("rapor", exist_ok=True)
_metin = json.dumps(sonuc, ensure_ascii=False, indent=1)
import re as _re  # güvenlik: rapora asla erişim anahtarı yazılmasın
_metin = _re.sub(r"access_token=[A-Za-z0-9]+", "access_token=REDACTED", _metin)
open("rapor/karsilastirma.json", "w", encoding="utf-8").write(_metin)
print("IG medya:", len(sonuc["ig_medya"] or []), "FB gönderi:", len(sonuc["fb_gonderi"] or []),
      "FB metrik:", list(sonuc["fb_sayfa"]), "hatalar:", list(hatalar))
