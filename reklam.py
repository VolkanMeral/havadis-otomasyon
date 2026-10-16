#!/usr/bin/env python3
"""
Reklam paylaşımı: reklam/reklamlar.json dosyasındaki planlı reklamları zamanı gelince paylaşır.

Her kayıt:
  id        benzersiz ad (ör. "tandir-2026-10-16")
  firma     reklamveren
  tarih     "YYYY-AA-GG" (Viyana saati)
  saat      "SS:DD"
  turler    ["gonderi", "reels", "story"] (bir veya birkaçı)
  gorseller ["reklam/tandir/xx.jpg", ...]  (birden fazlaysa gönderi karusel olur)
  metin     paylaşım metni (Instagram); Facebook'ta "📲 @hesap" satırı "📲 Instagram: @hesap" olur
  etiket    Instagram hesabı (görsel üzerine etiket ve Story yazısı için, @ işaretsiz)
  story     {"baslik": "...", "alt": "..."}  Story ve Reels üzerindeki kısa yazılar
  hemen     true ise saati beklemeden bir sonraki çalışmada paylaşılır

Bir kayıt, zamanı geldiğinde ve zamanından en fazla REKLAM_PENCERE saat (varsayılan 3) geçmişse paylaşılır.
Paylaşılanlar reklam/reklam_durum.json'a yazılır; aynı reklam iki kez paylaşılmaz (hata alan tür de tekrar denenmez,
çünkü Meta bazen hata döndürse de paylaşımı yapar: bunlar elle kontrol edilir).
DRY_RUN=1 iken sadece görsel/video üretilir.
"""
import datetime as dt
import json
import os
import subprocess
import sys
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image, ImageFilter

import havadis_bot as bot

KOK = bot.KOK
PLAN = os.path.join(KOK, "reklam", "reklamlar.json")
DURUM = os.path.join(KOK, "reklam", "reklam_durum.json")
CIKTI = os.path.join(KOK, "cikti", "reklam")
VIYANA = ZoneInfo("Europe/Vienna")
PENCERE = dt.timedelta(hours=float(os.getenv("REKLAM_PENCERE", "3")))
REKLAM_ETIKET = os.getenv("AD_LABEL", "Anzeige")
FPS = 30
SURE = 10.0
FONT = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:'
        'wght@700;800;900&family=Barlow:wght@500;600;700;800&display=swap">')

log = bot.log


# ---------------------------------------------------------------- plan ve durum

def plan_oku():
    return json.load(open(PLAN, encoding="utf-8"))["reklamlar"]


def durum_oku():
    return json.load(open(DURUM, encoding="utf-8")) if os.path.exists(DURUM) else {}


def durum_yaz(d):
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def zamani(r):
    return dt.datetime.strptime(f"{r['tarih']} {r.get('saat') or '12:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=VIYANA)


def sirasi_gelenler(plan, durum, simdi):
    sec = []
    for r in plan:
        kalan = [t for t in r["turler"] if t not in durum.get(r["id"], {})]
        if not kalan:
            continue
        z = zamani(r)
        if r.get("hemen") or (z <= simdi <= z + PENCERE):
            sec.append((r, kalan))
    return sec


# ---------------------------------------------------------------- görsel hazırlama

def _cover(img, w, h, odak=0.4):
    o = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
    x, y = (img.width - w) // 2, int((img.height - h) * odak)
    return img.crop((x, y, x + w, y + h))


def akis_gorseli(yol, cikti, w=1080, h=1350):
    """Instagram akışına uygun 4:5 görsel. Afişler kırpılmaz (bulanık zemin üstünde tam görünür), fotoğraflar kırpılır."""
    img = Image.open(yol).convert("RGB")
    afis = "afis" in os.path.basename(yol)
    if not afis:
        out = _cover(img, w, h)
    else:
        zemin = _cover(img, w, h).filter(ImageFilter.GaussianBlur(40))
        zemin = Image.eval(zemin, lambda v: int(v * 0.55))
        o = min(w / img.width, h / img.height)
        fg = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
        zemin.paste(fg, ((w - fg.width) // 2, (h - fg.height) // 2))
        out = zemin
    out.save(cikti, "JPEG", quality=92)
    return cikti


def tek_gorsel(yol, cikti):
    """Tek görselli gönderi: kare veya 4:5 arası ise olduğu gibi, değilse 4:5'e uyarlanır."""
    img = Image.open(yol).convert("RGB")
    oran = img.width / img.height
    if 0.8 <= oran <= 1.91:
        if img.width > 1440:
            img = img.resize((1440, round(1440 / oran)), Image.LANCZOS)
        img.save(cikti, "JPEG", quality=92)
        return cikti
    return akis_gorseli(yol, cikti)


def _ortak_css():
    return """
  html, body { margin: 0; padding: 0; }
  body { width: 1080px; height: 1920px; overflow: hidden; background: #070B14; color: #fff;
         font-family: 'Barlow', 'Helvetica Neue', Arial, sans-serif; }
  .zemin { position: absolute; inset: -80px; background-size: cover; background-position: center;
           filter: blur(60px) brightness(.45); }
  .etiket { position: absolute; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; font-size: 30px; }
  .baslik { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; font-weight: 900; text-transform: uppercase;
            line-height: .95; font-size: 96px; }
  .hesap { display: inline-block; background: #fff; color: #0A0A0A; font-weight: 800; font-size: 46px;
           padding: 14px 30px; border-radius: 18px; }
  .alt { font-weight: 600; font-size: 40px; color: #E3E5EA; }
"""


def story_html(r, afis_uri, oran=1.0):
    s = r.get("story", {})
    w = 940 if oran >= 1 else 820
    h = round(w / oran)
    ust = 300 if oran >= 1 else 250
    yazi_ust = ust + h + 60
    hesap = f'<span class="hesap">@{r["etiket"]}</span>' if r.get("etiket") else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">{FONT}<style>{_ortak_css()}
  .afis {{ position: absolute; left: {(1080 - w) // 2}px; top: {ust}px; width: {w}px; height: {h}px; border-radius: 26px;
           background-size: cover; background-position: center; box-shadow: 0 40px 120px rgba(0,0,0,.55); }}
  .yazi {{ position: absolute; left: 70px; right: 70px; top: {yazi_ust}px; display: flex; flex-direction: column;
           align-items: center; gap: 28px; text-align: center; }}
</style></head><body>
<div class="zemin" style="background-image:url('{afis_uri}')"></div>
<div class="afis" style="background-image:url('{afis_uri}')"></div>
<div class="yazi"><div class="baslik">{s.get('baslik', '')}</div>{hesap}<div class="alt">{s.get('alt', '')}</div></div>
<div class="etiket" lang="de" style="right:60px; bottom:60px">{REKLAM_ETIKET}</div>
</body></html>"""


def reels_html(r, afis_uri, logo_uri):
    s = r.get("story", {})
    hesap = f'<span class="hesap">@{r["etiket"]}</span>' if r.get("etiket") else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">{FONT}<style>{_ortak_css()}
  .kutu {{ position: absolute; left: 0; top: 330px; width: 1080px; height: 1080px; overflow: hidden; }}
  .afis {{ width: 1080px; height: 1080px; background-size: cover; background-position: center; }}
  .yazi {{ position: absolute; left: 70px; right: 70px; top: 1440px; display: flex; flex-direction: column;
           align-items: flex-start; gap: 20px; }}
  .perde, .kapanis {{ position: absolute; inset: 0; background: #070B14; }}
  .kapanis {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 40px; opacity: 0; z-index: 20; }}
  .perde {{ z-index: 19; }}
  .kapanis img {{ width: 620px; }}
  .kapanis span {{ font-weight: 800; letter-spacing: .1em; text-transform: uppercase; font-size: 30px; color: #A9AEBB; }}
</style></head><body>
<div class="zemin" style="background-image:url('{afis_uri}')"></div>
<div class="kutu"><div class="afis" style="background-image:url('{afis_uri}')"></div></div>
<div class="yazi"><div class="baslik" style="font-size:84px">{s.get('baslik', '')}</div>{hesap}</div>
<div class="etiket" lang="de" style="right:60px; top:230px; background:rgba(255,255,255,.16); padding:8px 16px; border-radius:8px">{REKLAM_ETIKET}</div>
<div class="perde"></div>
<div class="kapanis"><img src="{logo_uri}" alt="Havadis.at"><span lang="de">{REKLAM_ETIKET} · {r.get('firma', '')}</span></div>
<script>
  const q = s => document.querySelector(s);
  const ilerle = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
  const yum = x => 1 - Math.pow(1 - x, 3);
  window.kare = function (t) {{
    q('.afis').style.transform = `scale(${{1 + 0.1 * Math.min(t, {SURE - 2}) / {SURE - 2}}})`;
    q('.perde').style.opacity = 1 - yum(ilerle(t, 0, 0.9));
    const y = yum(ilerle(t, 1.0, 1.7));
    q('.yazi').style.opacity = y; q('.yazi').style.transform = `translateY(${{40 * (1 - y)}}px)`;
    const k = yum(ilerle(t, {SURE - 2}, {SURE - 1.5}));
    q('.kapanis').style.opacity = k;
    q('.kapanis img').style.transform = `scale(${{0.9 + 0.1 * yum(ilerle(t, {SURE - 2}, {SURE - 1}))}})`;
  }};
</script></body></html>"""


SLAYT_SN = 1.4  # çok görselli Reels'te her görselin ekranda kalma süresi


def reels_slayt_html(r, uriler, logo_uri, sure):
    """Birden çok görselli Reels: görseller sırayla geçer, sonda Havadis kapanışı."""
    hesap = f'<span class="hesap">@{r["etiket"]}</span>' if r.get("etiket") else ""
    slaytlar = "".join(f'<div class="slayt" style="background-image:url(\'{u}\')"></div>' for u in uriler)
    gecis = sure - 2
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8">{FONT}<style>{_ortak_css()}
  .kutu {{ position: absolute; left: 60px; top: 230px; width: 960px; height: 1200px; overflow: hidden; border-radius: 24px; isolation: isolate;
           box-shadow: 0 40px 120px rgba(0,0,0,.55); }}
  .slayt {{ position: absolute; inset: 0; background-size: cover; background-position: center; opacity: 0; }}
  .yazi {{ position: absolute; left: 60px; right: 60px; top: 1470px; display: flex; justify-content: space-between;
           align-items: center; }}
  .perde, .kapanis {{ position: absolute; inset: 0; background: #070B14; }}
  .kapanis {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 40px; opacity: 0; z-index: 20; }}
  .perde {{ z-index: 19; }}
  .kapanis img {{ width: 620px; }}
  .kapanis span {{ font-weight: 800; letter-spacing: .1em; text-transform: uppercase; font-size: 30px; color: #A9AEBB; }}
</style></head><body>
<div class="zemin" style="background-image:url('{uriler[0]}')"></div>
<div class="kutu">{slaytlar}</div>
<div class="yazi">{hesap}<span class="etiket" lang="de" style="position:static">{REKLAM_ETIKET}</span></div>
<div class="perde"></div>
<div class="kapanis"><img src="{logo_uri}" alt="Havadis.at"><span lang="de">{REKLAM_ETIKET} · {r.get('firma', '')}</span></div>
<script>
  const q = s => document.querySelector(s);
  const S = [...document.querySelectorAll('.slayt')];
  const ilerle = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
  const yum = x => 1 - Math.pow(1 - x, 3);
  const D = {gecis} / S.length;
  window.kare = function (t) {{
    S.forEach((el, i) => {{
      const a = i * D;
      const op = i === 0 ? 1 : ilerle(t, a - 0.3, a);
      el.style.opacity = op;
      el.style.zIndex = i;
      el.style.transform = `scale(${{1 + 0.06 * ilerle(t, a - 0.3, a + D)}})`;
    }});
    q('.perde').style.opacity = 1 - yum(ilerle(t, 0, 0.6));
    const k = yum(ilerle(t, {gecis}, {gecis + 0.5}));
    q('.kapanis').style.opacity = k;
    q('.kapanis img').style.transform = `scale(${{0.9 + 0.1 * yum(ilerle(t, {gecis}, {gecis + 1}))}})`;
  }};
</script></body></html>"""


def _sayfa(p, html_):
    s = p.new_page(viewport={"width": 1080, "height": 1920})
    s.set_content(html_, wait_until="networkidle", timeout=60000)
    s.evaluate("document.fonts.ready")
    return s


def story_uret(r, afis, cikti):
    from playwright.sync_api import sync_playwright
    uri = bot.veri_uri(afis, "image/jpeg")
    with sync_playwright() as p:
        b = p.chromium.launch()
        with Image.open(afis) as im:
            oran = max(0.75, min(1.0, im.width / im.height))
        s = _sayfa(b, story_html(r, uri, oran))
        Image.open(BytesIO(s.screenshot())).convert("RGB").save(cikti, "JPEG", quality=92)
        b.close()
    return cikti


def reels_uret(r, kaynaklar, cikti):
    from playwright.sync_api import sync_playwright
    logo = bot.veri_uri(os.path.join(KOK, "assets", "logo-beyaz.png"), "image/png")
    if len(kaynaklar) > 1:
        uriler = []
        for i, k in enumerate(kaynaklar):
            yol = akis_gorseli(k, cikti.replace(".mp4", f"-slayt{i + 1}.jpg"), 960, 1200)
            uriler.append(bot.veri_uri(yol, "image/jpeg"))
        sure = round(2 + SLAYT_SN * len(uriler), 2)
        html_ = reels_slayt_html(r, uriler, logo, sure)
    else:
        sure = SURE
        html_ = reels_html(r, bot.veri_uri(kaynaklar[0], "image/jpeg"), logo)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100", "-t", str(sure),
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch()
        s = _sayfa(b, html_)
        for i in range(int(sure * FPS)):
            s.evaluate(f"() => window.kare({i / FPS})")
            ff.stdin.write(s.screenshot(type="jpeg", quality=92))
        b.close()
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg reklam videosunu oluşturamadı")
    kapak = cikti.replace(".mp4", "-kapak.jpg")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "4", "-i", cikti, "-frames:v", "1", "-q:v", "2", kapak],
                   check=True)
    return cikti, kapak


# ---------------------------------------------------------------- Meta paylaşımları

def fb_metin(r):
    return r["metin"].replace("📲 @", "📲 Instagram: @")


def fb_gizli_foto(yol):
    """Fotoğrafı Facebook'a yayınlamadan yükler; Instagram'ın istediği herkese açık adresi ve foto kimliğini döndürür."""
    with open(yol, "rb") as f:
        sonuc = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.PAGE_ID}/photos"), timeout=120,
                                          data={"published": "false", "access_token": bot.PAGE_TOKEN},
                                          files={"source": ("g.jpg", f, "image/jpeg")}))
    bilgi = bot.kontrol(bot.HTTP.get(bot.graph(sonuc["id"]), timeout=30,
                                     params={"fields": "images", "access_token": bot.PAGE_TOKEN}))
    return sonuc["id"], max(bilgi["images"], key=lambda i: i["width"])["source"]


def ig_gorsel(adres, metin, etiket=None):
    """Instagram tek görsel; mümkünse reklamverenin hesabını görselin üzerine etiketler."""
    def gonder(etiketli):
        veri = {"image_url": adres, "caption": metin, "access_token": bot.PAGE_TOKEN}
        if etiketli:
            veri["user_tags"] = json.dumps([{"username": etiket, "x": 0.5, "y": 0.92}])
        kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), data=veri, timeout=60))
        bot.ig_bekle(kap["id"])
        return bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media_publish"), timeout=60,
                                         data={"creation_id": kap["id"], "access_token": bot.PAGE_TOKEN}))["id"]
    if etiket:
        try:
            return gonder(True)
        except Exception as e:
            log("Etiketli paylaşım olmadı, etiketsiz deneniyor:", e)
    return gonder(False)


def ig_story_gorsel(adres):
    kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
        "image_url": adres, "media_type": "STORIES", "access_token": bot.PAGE_TOKEN}))
    bot.ig_bekle(kap["id"])
    return bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media_publish"), timeout=60,
                                     data={"creation_id": kap["id"], "access_token": bot.PAGE_TOKEN}))["id"]


def fb_story_gorsel(foto_id):
    return bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.PAGE_ID}/photo_stories"), timeout=60,
                                     data={"photo_id": foto_id, "access_token": bot.PAGE_TOKEN})).get("post_id", foto_id)


# ---------------------------------------------------------------- ana akış

def reklam_isle(r, turler, durum):
    import karusel
    klasor = os.path.join(CIKTI, r["id"])
    os.makedirs(klasor, exist_ok=True)
    kaynak = [os.path.join(KOK, g) for g in r["gorseller"]]
    kayit = durum.setdefault(r["id"], {})

    hazir = {}
    if "gonderi" in turler:
        if len(kaynak) > 1:
            hazir["gonderi"] = [akis_gorseli(k, os.path.join(klasor, f"karusel-{i + 1}.jpg")) for i, k in enumerate(kaynak)]
        else:
            hazir["gonderi"] = [tek_gorsel(kaynak[0], os.path.join(klasor, "gonderi.jpg"))]
    if "reels" in turler:
        reels_kaynak = [os.path.join(KOK, g) for g in r.get("reels_gorseller", [])] or kaynak[:1]
        hazir["reels"] = reels_uret(r, reels_kaynak, os.path.join(klasor, "reels.mp4"))
    if "story" in turler:
        story_kaynak = os.path.join(KOK, r["story_gorsel"]) if r.get("story_gorsel") else kaynak[0]
        hazir["story"] = story_uret(r, story_kaynak, os.path.join(klasor, "story.jpg"))
    log(f"{r['id']}: hazır ->", ", ".join(hazir))

    if bot.DRY_RUN:
        log("DENEME MODU: reklam paylaşılmadı.")
        return
    zaman = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    def dene(tur, ad, is_):
        try:
            kayit.setdefault(tur, {"zaman": zaman})[ad] = is_()
            log(f"{r['id']} {ad} paylaşıldı:", kayit[tur][ad])
        except Exception as e:
            kayit.setdefault(tur, {"zaman": zaman})[ad + "_hata"] = str(e)[:300]
            log(f"{r['id']} {ad} hatası:", e)
            bot.gh_hata(f"Reklam {r['id']} {ad} hatası", e)
        durum_yaz(durum)

    if "gonderi" in turler:
        gorseller = hazir["gonderi"]
        if len(gorseller) > 1:
            def fb_karusel():
                fb_id, adresler = karusel.facebook_coklu(gorseller, fb_metin(r))
                kayit.setdefault("gonderi", {"zaman": zaman})["_adresler"] = adresler
                return fb_id
            dene("gonderi", "facebook", fb_karusel)
            adresler = kayit.get("gonderi", {}).pop("_adresler", None)
            if adresler and bot.IG_USER_ID:
                dene("gonderi", "instagram", lambda: karusel.instagram_karusel(adresler, r["metin"]))
        else:
            sonuc = {}

            def fb_tek():
                fb_id, adres = bot.facebook_paylas(gorseller[0], fb_metin(r))
                sonuc["adres"] = adres
                return fb_id
            dene("gonderi", "facebook", fb_tek)
            if sonuc.get("adres") and bot.IG_USER_ID:
                dene("gonderi", "instagram", lambda: ig_gorsel(sonuc["adres"], r["metin"], r.get("etiket")))

    if "reels" in turler:
        video, kapak = hazir["reels"]
        dene("reels", "facebook", lambda: bot.facebook_reel(video, fb_metin(r), kapak))
        if bot.IG_USER_ID:
            dene("reels", "instagram", lambda: bot.instagram_video(video, "REELS", r["metin"]))

    if "story" in turler:
        foto = {}

        def yukle():
            foto["id"], foto["adres"] = fb_gizli_foto(hazir["story"])
            return foto["id"]
        dene("story", "yukleme", yukle)
        if foto.get("adres"):
            if bot.IG_USER_ID:
                dene("story", "instagram", lambda: ig_story_gorsel(foto["adres"]))
            dene("story", "facebook", lambda: fb_story_gorsel(foto["id"]))


def main():
    os.makedirs(CIKTI, exist_ok=True)
    simdi = dt.datetime.now(VIYANA)
    plan, durum = plan_oku(), durum_oku()
    gelenler = sirasi_gelenler(plan, durum, simdi)
    if not gelenler:
        log("Şu an paylaşılacak reklam yok.", simdi.strftime("%Y-%m-%d %H:%M"))
        return 0
    if not bot.DRY_RUN and not (bot.PAGE_ID and bot.PAGE_TOKEN):
        log("HATA: META_PAGE_ID / META_PAGE_TOKEN tanımlı değil.")
        return 1
    for r, turler in gelenler:
        log(f"Reklam: {r['id']} ({r.get('firma')}) -> {', '.join(turler)}")
        reklam_isle(r, turler, durum)
    return 0


if __name__ == "__main__":
    sys.exit(main())
