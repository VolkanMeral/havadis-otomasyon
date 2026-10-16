#!/usr/bin/env python3
"""TikTok bağlantısı (Content Posting API).

Şu anki mod: TASLAK (inbox). Video, TikTok uygulamasındaki gelen kutusuna/taslaklara gider;
Havadis hesabına bildirim düşer, tek dokunuşla (istenirse popüler bir ses eklenerek) yayınlanır.
TikTok aynı anda en fazla 5 bekleyen taslağa izin verir, bu yüzden günde en çok 5 video gönderilir.
Uygulama TikTok incelemesinden (audit) geçince TIKTOK_MODE=direct ile doğrudan herkese açık paylaşım açılır.

Anahtarlar:
- TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET (GitHub secrets): TikTok geliştirici uygulamasının bilgileri.
- Şifreleme anahtarı TIKTOK_CLIENT_SECRET'tan türetilir (ayrı bir secret gerekmez; istenirse TIKTOK_TOKEN_KEY).
- tiktok_token.enc (depoda, ŞİFRELİ): TikTok'un yenileme anahtarı (refresh token). Erişim anahtarı 24 saatte
  bir sona erdiği için her paylaşımda yenilenir; TikTok yenileme anahtarını değiştirirse dosya güncellenir
  ve iş akışı onu depoya kaydeder.

Kurulum (bir kez):  python tiktok.py baglan <yetki_kodu>   (GitHub'da "tiktok_kod" girdisiyle çalışır)
Bağlantı adresi:    python tiktok.py adres
"""
import json
import os
import sys
import time
import urllib.parse

import requests

KOK = os.path.dirname(os.path.abspath(__file__))
TOKEN_DOSYASI = os.path.join(KOK, "tiktok_token.enc")
API = "https://open.tiktokapis.com/v2"
CLIENT_KEY = (os.getenv("TIKTOK_CLIENT_KEY") or "").strip()
CLIENT_SECRET = (os.getenv("TIKTOK_CLIENT_SECRET") or "").strip()
SIFRE = (os.getenv("TIKTOK_TOKEN_KEY") or "").strip()
if not SIFRE and CLIENT_SECRET:
    import base64, hashlib
    SIFRE = base64.urlsafe_b64encode(hashlib.sha256(f"havadis-tiktok:{CLIENT_SECRET}".encode()).digest()).decode()
YONLENDIRME = os.getenv("TIKTOK_REDIRECT_URI", "https://havadis.at/")
MOD = os.getenv("TIKTOK_MODE", "inbox").strip() or "inbox"   # inbox (taslak) | direct (audit sonrası)
KAPSAMLAR = "user.info.basic,video.upload,video.publish"
HTTP = requests.Session()
HTTP.headers["User-Agent"] = "HavadisSosyalMedyaBot/1.0 (+https://havadis.at)"


def hazir_mi():
    return bool(CLIENT_KEY and CLIENT_SECRET and SIFRE and os.path.exists(TOKEN_DOSYASI))


def _fernet():
    from cryptography.fernet import Fernet
    return Fernet(SIFRE.encode())


def _oku():
    with open(TOKEN_DOSYASI, "rb") as f:
        return json.loads(_fernet().decrypt(f.read()))


def _yaz(veri):
    with open(TOKEN_DOSYASI, "wb") as f:
        f.write(_fernet().encrypt(json.dumps(veri).encode()))


def _token_iste(veri):
    r = HTTP.post(f"{API}/oauth/token/", data={"client_key": CLIENT_KEY, "client_secret": CLIENT_SECRET, **veri},
                  headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    j = r.json()
    if r.status_code >= 400 or "access_token" not in j:
        hata = {k: j.get(k) for k in ("error", "error_description", "log_id")}
        raise RuntimeError(f"TikTok anahtar hatası {r.status_code}: {hata}")
    eski = _oku() if os.path.exists(TOKEN_DOSYASI) else {}
    if eski.get("refresh_token") != j["refresh_token"]:  # değişmediyse dosyaya dokunma (gereksiz commit olmasın)
        _yaz({"refresh_token": j["refresh_token"], "open_id": j.get("open_id"),
              "refresh_bitis": int(time.time()) + int(j.get("refresh_expires_in", 0)), "kapsam": j.get("scope")})
    return j["access_token"]


def adres():
    """Kullanıcının bir kez açıp izin vereceği TikTok bağlantı adresi."""
    return "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode({
        "client_key": CLIENT_KEY, "scope": KAPSAMLAR, "response_type": "code",
        "redirect_uri": YONLENDIRME, "state": "havadis"})


def baglan(kod):
    """İzin sonrası adres çubuğundaki ?code=... değerini kalıcı (şifreli) anahtara çevirir."""
    kod = urllib.parse.unquote(kod.strip())
    if "code=" in kod:  # adresin tamamı yapıştırıldıysa
        kod = urllib.parse.parse_qs(urllib.parse.urlparse(kod).query)["code"][0]
    _token_iste({"grant_type": "authorization_code", "code": kod, "redirect_uri": YONLENDIRME})
    return "TikTok bağlandı."


def erisim():
    """24 saatlik erişim anahtarını yeniler (yenileme anahtarı değişirse dosya güncellenir)."""
    return _token_iste({"grant_type": "refresh_token", "refresh_token": _oku()["refresh_token"]})


def kalan_gun():
    return (_oku().get("refresh_bitis", 0) - time.time()) / 86400


def _kontrol(r):
    j = r.json()
    if r.status_code >= 400 or j.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok hatası {r.status_code}: {j.get('error')}")
    return j.get("data", {})


def paylas(video, baslik=""):
    """Videoyu TikTok'a gönderir. inbox: taslak (kullanıcı yayınlar). direct: doğrudan herkese açık."""
    token = erisim()
    bas = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    boyut = os.path.getsize(video)
    kaynak = {"source": "FILE_UPLOAD", "video_size": boyut, "chunk_size": boyut, "total_chunk_count": 1}
    if MOD == "direct":
        bilgi = _kontrol(HTTP.post(f"{API}/post/publish/creator_info/query/", headers=bas, timeout=30))
        gizlilik = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in bilgi.get("privacy_level_options", []) \
            else bilgi.get("privacy_level_options", ["SELF_ONLY"])[0]
        govde = {"post_info": {"title": baslik[:2200], "privacy_level": gizlilik, "is_aigc": True,
                               "disable_comment": False, "disable_duet": False, "disable_stitch": False},
                 "source_info": kaynak}
        uc = f"{API}/post/publish/video/init/"
    else:
        govde, uc = {"source_info": kaynak}, f"{API}/post/publish/inbox/video/init/"
    veri = _kontrol(HTTP.post(uc, headers=bas, json=govde, timeout=60))
    with open(video, "rb") as f:
        r = HTTP.put(veri["upload_url"], data=f.read(), timeout=300, headers={
            "Content-Type": "video/mp4", "Content-Length": str(boyut),
            "Content-Range": f"bytes 0-{boyut - 1}/{boyut}"})
    if r.status_code >= 400:
        raise RuntimeError(f"TikTok yükleme hatası {r.status_code}: {r.text[:300]}")
    return veri["publish_id"]


if __name__ == "__main__":
    komut = sys.argv[1] if len(sys.argv) > 1 else ""
    if komut == "adres":
        print(adres())
    elif komut == "baglan":
        print(baglan(sys.argv[2]))
        print(f"Yenileme anahtarı {kalan_gun():.0f} gün geçerli.")
    elif komut == "kontrol":
        erisim()
        print(f"TikTok erişimi tamam. Yenileme anahtarı {kalan_gun():.0f} gün geçerli.")
    else:
        print(__doc__)
