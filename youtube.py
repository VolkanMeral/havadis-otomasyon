#!/usr/bin/env python3
"""YouTube bağlantısı: haber videolarını Shorts olarak yükler (YouTube Data API v3).

Dikey (9:16) ve 3 dakikadan kısa videolar YouTube'da otomatik olarak Shorts olur.
Resmî belgelere göre videos.insert günde 100 çağrıya kadar izinlidir; sistem günde ~10 video yükler.

Anahtarlar (GitHub secrets):
- YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET: Google Cloud'daki OAuth istemcisinin bilgileri
- YOUTUBE_REFRESH_TOKEN: kanal hesabıyla bir kez izin verilerek alınan yenileme anahtarı
  (Google OAuth Playground ile alınır; OAuth onay ekranı "In production" olmalı, yoksa 7 günde geçersiz olur)
Üçü de tanımlı değilse YouTube adımı atlanır.

Kontrol: python youtube.py kontrol   (kanal adını yazar, paylaşım yapmaz)
"""
import json
import os
import re
import sys

import requests

CLIENT_ID = (os.getenv("YOUTUBE_CLIENT_ID") or "").strip()
CLIENT_SECRET = (os.getenv("YOUTUBE_CLIENT_SECRET") or "").strip()
REFRESH_TOKEN = (os.getenv("YOUTUBE_REFRESH_TOKEN") or "").strip()
GIZLILIK = os.getenv("YOUTUBE_PRIVACY", "public").strip() or "public"   # public | unlisted | private
KATEGORI = "25"  # YouTube "Haberler ve Politika"
HTTP = requests.Session()
HTTP.headers["User-Agent"] = "HavadisSosyalMedyaBot/1.0 (+https://havadis.at)"


def hazir_mi():
    return bool(CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN)


def _erisim():
    r = HTTP.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"})
    j = r.json()
    if "access_token" not in j:
        ipucu = ""
        if j.get("error") == "invalid_grant":
            ipucu = (" (Yenileme anahtarı geçersiz ya da süresi dolmuş. OAuth onay ekranı 'Testing' durumundaysa "
                     "anahtarlar 7 günde biter: 'In production' yapıp anahtarı yeniden alın.)")
        raise RuntimeError(f"YouTube anahtar hatası: {j.get('error')} {j.get('error_description', '')}{ipucu}")
    return j["access_token"]


def _temiz(metin, n):
    """YouTube başlık/açıklamada < ve > kabul etmez; uzunluk sınırına göre kısaltır."""
    metin = re.sub(r"[<>]", "", metin or "").strip()
    return metin if len(metin) <= n else metin[: n - 1].rsplit(" ", 1)[0] + "…"


def kontrol():
    token = _erisim()
    r = HTTP.get("https://www.googleapis.com/youtube/v3/channels", timeout=30,
                 params={"part": "snippet,statistics", "mine": "true"},
                 headers={"Authorization": f"Bearer {token}"})
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"YouTube kanal hatası: {j['error'].get('message')}")
    if not j.get("items"):
        raise RuntimeError("Bu Google hesabına bağlı YouTube kanalı bulunamadı (izin verirken doğru kanalı seçin).")
    k = j["items"][0]
    return f"{k['snippet']['title']} ({k['statistics'].get('subscriberCount', '?')} abone)"


def yukle(video, baslik, aciklama, etiketler=()):
    """Videoyu yükler, video kimliğini döndürür."""
    token = _erisim()
    boyut = os.path.getsize(video)
    govde = {
        "snippet": {"title": _temiz(baslik, 100), "description": _temiz(aciklama, 4900),
                    "tags": [t.lstrip("#") for t in etiketler][:15], "categoryId": KATEGORI,
                    "defaultLanguage": "tr", "defaultAudioLanguage": "tr"},
        "status": {"privacyStatus": GIZLILIK, "selfDeclaredMadeForKids": False, "embeddable": True},
    }
    bas = HTTP.post("https://www.googleapis.com/upload/youtube/v3/videos", timeout=60,
                    params={"uploadType": "resumable", "part": "snippet,status"},
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(boyut)},
                    data=json.dumps(govde))
    if bas.status_code >= 400 or "Location" not in bas.headers:
        raise RuntimeError(f"YouTube yükleme başlatılamadı {bas.status_code}: {bas.text[:300]}")
    with open(video, "rb") as f:
        r = HTTP.put(bas.headers["Location"], data=f, timeout=300,
                     headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"})
    j = r.json() if r.content else {}
    if r.status_code >= 400 or "id" not in j:
        raise RuntimeError(f"YouTube yükleme hatası {r.status_code}: {r.text[:300]}")
    return j["id"]


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "kontrol":
    if not hazir_mi():
        print("YouTube anahtarları tanımlı değil (YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN).")
        sys.exit(0)
    try:
        print("YouTube kanalı erişilebilir:", kontrol())
    except Exception as e:
        print(f"::error title=YouTube bağlantı hatası::{e}")
        sys.exit(1)
