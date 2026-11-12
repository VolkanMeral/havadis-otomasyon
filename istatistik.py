#!/usr/bin/env python3
"""Paylaşımların istatistiklerini Meta'dan okur (sadece okuma). Sonuç: rapor/istatistik.json"""
import datetime as dt
import json
import os

import havadis_bot as bot

G = bot.graph
TOKEN = bot.PAGE_TOKEN
hatalar = {}


def al(yol, **p):
    p["access_token"] = TOKEN
    r = bot.HTTP.get(G(yol), params=p, timeout=60)
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


sonuc = {"zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "instagram": [], "facebook": []}

# ---- Instagram: hesap özeti
sonuc["ig_hesap"] = dene("ig_hesap", lambda: al(bot.IG_USER_ID, fields="username,followers_count,media_count"))
sonuc["ig_hesap_insights"] = dene("ig_hesap_insights", lambda: al(
    f"{bot.IG_USER_ID}/insights", metric="reach,views,profile_views,website_clicks,accounts_engaged",
    period="day", metric_type="total_value", since=int((dt.datetime.now() - dt.timedelta(days=2)).timestamp()),
    until=int(dt.datetime.now().timestamp())))

# ---- Instagram: son paylaşımlar
medya = dene("ig_medya", lambda: al(f"{bot.IG_USER_ID}/media", limit=40,
            fields="id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink")) or {}
for m in medya.get("data", []):
    tur = m.get("media_product_type")
    metrikler = "views,reach,likes,comments,shares,saved,total_interactions"
    if tur == "STORY":
        metrikler = "views,reach,replies,total_interactions"
    ins = dene(f"ig_insights_{tur}", lambda: al(f"{m['id']}/insights", metric=metrikler))
    if ins:
        m["insights"] = {d["name"]: (d.get("values") or [{}])[0].get("value", d.get("total_value", {}).get("value"))
                         for d in ins.get("data", [])}
    m["caption"] = (m.get("caption") or "").split("\n")[0][:90]
    sonuc["instagram"].append(m)

# Story'ler /media listesinde çıkmaz
st = dene("ig_stories", lambda: al(f"{bot.IG_USER_ID}/stories", fields="id,media_type,timestamp,permalink")) or {}
for m in st.get("data", []):
    ins = dene("ig_insights_STORY", lambda: al(f"{m['id']}/insights", metric="views,reach,replies"))
    if ins:
        m["insights"] = {d["name"]: (d.get("values") or [{}])[0].get("value") for d in ins.get("data", [])}
    m["media_product_type"] = "STORY"
    sonuc["instagram"].append(m)

# ---- Facebook: son gönderiler
fb = dene("fb_gonderiler", lambda: al(f"{bot.PAGE_ID}/posts", limit=40,
          fields="id,message,created_time,permalink_url,shares,reactions.summary(true).limit(0),comments.summary(true).limit(0)")) or {}
for p in fb.get("data", []):
    k = {"id": p["id"], "zaman": p.get("created_time"), "baslik": (p.get("message") or "").split("\n")[0][:90],
         "link": p.get("permalink_url"), "tepki": p.get("reactions", {}).get("summary", {}).get("total_count"),
         "yorum": p.get("comments", {}).get("summary", {}).get("total_count"), "paylasim": p.get("shares", {}).get("count", 0)}
    for metrik in ("post_media_view", "post_impressions", "post_impressions_unique"):
        ins = dene(f"fb_{metrik}", lambda: al(f"{p['id']}/insights", metric=metrik))
        if ins and ins.get("data"):
            k[metrik] = ins["data"][0]["values"][0]["value"]
    sonuc["facebook"].append(k)

# ---- Facebook sayfa özeti
sonuc["fb_sayfa"] = dene("fb_sayfa", lambda: al(bot.PAGE_ID, fields="name,followers_count,fan_count"))
sonuc["hatalar"] = hatalar
os.makedirs("rapor", exist_ok=True)
_metin = json.dumps(sonuc, ensure_ascii=False, indent=1)
import re as _re  # güvenlik: rapora asla erişim anahtarı yazılmasın
_metin = _re.sub(r"access_token=[A-Za-z0-9]+", "access_token=REDACTED", _metin)
open("rapor/istatistik.json", "w", encoding="utf-8").write(_metin)
print("IG:", len(sonuc["instagram"]), "FB:", len(sonuc["facebook"]), "hatalar:", list(hatalar))
