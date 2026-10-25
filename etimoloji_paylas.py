"""Kelimelerin Gizli Tarihi – takvimdeki onaylı bölümü saatinde FB Reels, IG Reels ve YouTube Shorts'ta paylaşır.
Kullanım: python etimoloji_paylas.py [--zorla <kelime>]   (DRY_RUN=1 ise paylaşmaz)"""
import datetime as dt, json, os, subprocess, sys
from zoneinfo import ZoneInfo
import havadis_bot as bot

TAKVIM = "etimoloji/yayin/takvim.json"
VIDEO_DALI = "etimoloji-video"
PENCERE_DK = 40  # slot saatinden en fazla bu kadar sonra paylaşılır (gecikmeli cron için)

def simdi(): return dt.datetime.now(ZoneInfo("Europe/Vienna"))

def sec(takvim, zorla=None):
    if zorla:
        return next((k for k in takvim["kayitlar"] if k["kelime"] == zorla), None)
    n = simdi()
    for k in takvim["kayitlar"]:
        if k.get("paylasildi") or not k.get("onay"): continue
        h, m = map(int, k["saat"].split(":"))
        hedef = dt.datetime.fromisoformat(k["tarih"]).replace(hour=h, minute=m, tzinfo=ZoneInfo("Europe/Vienna"))
        if dt.timedelta(minutes=-5) <= n - hedef <= dt.timedelta(minutes=PENCERE_DK):
            return k
    return None

def indir(kelime):
    """Videolar ana dalı şişirmesin diye ayrı 'etimoloji-video' dalında duruyor."""
    os.makedirs("etimoloji_tmp", exist_ok=True)
    subprocess.run(["git", "fetch", "--depth", "1", "origin", VIDEO_DALI], check=True)
    for ad in (f"{kelime}.mp4", f"kapak_{kelime}.jpg"):
        with open(f"etimoloji_tmp/{ad}", "wb") as f:
            f.write(subprocess.run(["git", "show", f"FETCH_HEAD:{ad}"], check=True, capture_output=True).stdout)
    return f"etimoloji_tmp/{kelime}.mp4", f"etimoloji_tmp/kapak_{kelime}.jpg"

def main():
    zorla = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == "--zorla" else None
    takvim = json.load(open(TAKVIM, encoding="utf-8"))
    k = sec(takvim, zorla)
    if not k:
        bot.log("Şu an paylaşılacak onaylı etimoloji bölümü yok."); return 0
    m = json.load(open(f"etimoloji/yayin/metinler/{k['kelime']}.json", encoding="utf-8"))
    bot.log(f"Etimoloji bölümü: {k['kelime']} ({k['tarih']} {k['saat']})")
    if bot.DRY_RUN:
        bot.log("DENEME MODU – paylaşılmadı.\n--- Facebook metni ---\n" + m["facebook"]); return 0
    video, kapak = indir(k["kelime"])
    sonuc = {}
    def dene(ad, is_):
        try:
            sonuc[ad] = is_(); bot.log(f"{ad} paylaşıldı:", sonuc[ad])
        except Exception as e:
            sonuc[f"{ad}_hata"] = str(e)[:300]; bot.log(f"{ad} hatası:", e)
            bot.gh_hata(f"Etimoloji – {ad} hatası", e)
    dene("facebook_reel", lambda: bot.facebook_reel(video, m["facebook"], kapak))
    if bot.IG_USER_ID:
        dene("instagram_reel", lambda: bot.instagram_video(video, "REELS", m["instagram"]))
    import youtube
    if youtube.hazir_mi():
        dene("youtube", lambda: youtube.yukle(video, m["youtube_baslik"], m["youtube_aciklama"], m.get("etiketler", [])))
    if any(x in sonuc for x in ("facebook_reel", "instagram_reel", "youtube")):
        k["paylasildi"] = simdi().isoformat(timespec="seconds"); k["sonuc"] = sonuc
        json.dump(takvim, open(TAKVIM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 0
    raise RuntimeError("Etimoloji bölümü hiçbir platformda paylaşılamadı.")

if __name__ == "__main__":
    sys.exit(main())
