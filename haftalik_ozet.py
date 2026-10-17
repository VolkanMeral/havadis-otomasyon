#!/usr/bin/env python3
"""Haftalık özet videosu: "Avusturya'da bu hafta" – seslendirme yok, özgün müzik + ekranda yazı.
Her pazar 11:00 (Viyana) Facebook Reels, Instagram Reels ve YouTube Shorts olarak paylaşılır.

Akış (en fazla ~88 sn; Facebook Reels sınırı 90 sn):
  giriş (3,5 sn) → 4–6 haber (her biri yazı uzunluğuna göre 7–13 sn) → kapanış (4 sn, logo + takip çağrısı)
Elle deneme: GitHub'da paylaşım görevini is=ozet, dry_run=1 ile çalıştırın (video üretilir, paylaşılmaz).
Yerelde:     python haftalik_ozet.py <çıktı.mp4>"""
import datetime as dt
import html
import json
import os
import subprocess
import sys

import havadis_bot as bot
import karusel
import muzik_uret

E = html.escape
FPS = 24
W, H = 1080, 1920
EN_FAZLA = 88.0
GIRIS, KAPANIS = 3.5, 4.0
KATEGORILER = {bot.kat_norm(k) for k in os.getenv("OZET_CATEGORIES", "Avusturya,Vorarlberg").split(",") if k.strip()}
BASLIK = os.getenv("OZET_TITLE", "Avusturya’da|bu hafta")   # "|" sonrası kırmızı bantta


def haftanin_haberleri(adet=6):
    """Son 7 günün haberleri: önce her günden bir haber (kategoriler sırayla), sonra kalanlar."""
    simdi = dt.datetime.now(dt.timezone.utc)
    adaylar = []
    for h in bot.arsiv_oku():
        t = dt.datetime.fromisoformat(h["tarih"]) if h.get("tarih") else None
        if t and (simdi - t).days < 7 and h.get("resim") and bot.kategori_eslesir(h["kategori"], KATEGORILER):
            adaylar.append(dict(h, tarih=t))
    adaylar.sort(key=lambda h: h["tarih"], reverse=True)
    secilen, gunler = [], set()
    for h in adaylar:
        if h["tarih"].date() not in gunler:
            secilen.append(h)
            gunler.add(h["tarih"].date())
    for h in adaylar:
        if h not in secilen:
            secilen.append(h)
    return secilen[: adet * 2]  # süreye sığanlar aşağıda seçilir


def kisa_ozet(metin, n=200):
    """Özetin ilk cümle(ler)i: cümle ortasında kesilmesin diye cümle sınırında durur."""
    import re
    cumleler = re.split(r"(?<=[.!?…])\s+", (metin or "").strip())
    sonuc = ""
    for c in cumleler:
        if sonuc and len(sonuc) + len(c) + 1 > n:
            break
        sonuc = f"{sonuc} {c}".strip()
    return sonuc if len(sonuc) <= n + 60 else bot.kisalt(sonuc, n)


def okuma_suresi(h):
    return max(7.0, min(13.0, 4.0 + len(h["baslik"] + " " + h["ozet_kisa"]) / 17))


def foto(url, w, h):
    r = bot.HTTP.get(url, timeout=60)
    r.raise_for_status()
    return karusel.foto_uri(r.content, w, h)


CSS = """
html, body { margin: 0; padding: 0; } body { width: 1080px; height: 1920px; overflow: hidden; background: #070B14; }
.v { position: relative; width: 1080px; height: 1920px; overflow: hidden; color: #fff; font-family: 'Barlow', Arial, sans-serif; background: #070B14; }
.kos { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; }
.b { position: absolute; inset: 0; opacity: 0; display: none; }
.ust { position: absolute; left: 64px; right: 64px; top: 230px; display: flex; justify-content: space-between; align-items: center; z-index: 5; }
.ust img { width: 220px; display: block; }
.ust .sag { text-align: right; }
.etiket { display: inline-block; background: #E42320; font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 28px; letter-spacing: 3px; padding: 8px 16px; }
.ki { font-size: 20px; color: rgba(255,255,255,.65); margin-top: 8px; }
.ki:empty { display: none; }
.cubuk { position: absolute; left: 64px; right: 64px; top: 318px; height: 6px; background: rgba(255,255,255,.18); z-index: 5; }
.cubuk i { display: block; height: 100%; width: 0; background: #E42320; }
.foto { position: absolute; left: 0; top: 350px; width: 1080px; height: 620px; overflow: hidden; }
.foto img { width: 100%; height: 100%; object-fit: cover; display: block; }
.foto::after { content: ""; position: absolute; inset: 0; background: linear-gradient(rgba(7,11,20,.35), rgba(7,11,20,0) 25%, rgba(7,11,20,0) 60%, #070B14); }
.bilgi { position: absolute; left: 64px; right: 64px; top: 930px; bottom: 300px; display: flex; flex-direction: column; gap: 22px; overflow: hidden; }
.ust2 { display: flex; align-items: baseline; gap: 18px; }
.no { font-size: 92px; line-height: .8; font-weight: 900; color: #E42320; }
.gun { font-size: 30px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.75); }
.kat { font-size: 26px; font-weight: 800; letter-spacing: 3px; background: rgba(255,255,255,.12); padding: 4px 12px; text-transform: uppercase; }
.bilgi h2 { margin: 0; font-size: 72px; line-height: 1.02; font-weight: 900; text-transform: uppercase; }
.bilgi p { margin: 0; font-size: 42px; line-height: 1.32; font-weight: 600; color: #E4E8EF;
           display: -webkit-box; -webkit-line-clamp: 6; -webkit-box-orient: vertical; overflow: hidden;
           border-left: 8px solid #E42320; padding-left: 28px; }
.arka { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.karart { position: absolute; inset: 0; background: linear-gradient(rgba(7,11,20,.7), rgba(7,11,20,.88) 50%, #070B14); }
.giris { position: absolute; left: 64px; right: 64px; top: 560px; }
.giris h1 { margin: 0; white-space: nowrap; font-size: 150px; line-height: .95; font-weight: 900; text-transform: uppercase; }
.bant { background: #E42320; padding: 0 14px; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
.aralik { margin-top: 30px; font-size: 42px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.85); }
.liste { margin-top: 46px; display: flex; flex-direction: column; gap: 14px; font-size: 36px; font-weight: 600; color: rgba(255,255,255,.8); }
.liste span b { color: #E42320; font-weight: 900; margin-right: 12px; }
.kapanis { position: absolute; left: 64px; right: 64px; top: 520px; display: flex; flex-direction: column; align-items: center; gap: 46px; text-align: center; }
.kapanis img { width: 600px; }
.kapanis .cta { font-size: 70px; font-weight: 900; text-transform: uppercase; line-height: 1.1; }
.kapanis .takip { font-size: 44px; font-weight: 700; color: rgba(255,255,255,.9); line-height: 1.4; }
.kapanis .takip small { display: block; font-size: 32px; font-weight: 600; color: rgba(255,255,255,.65); }
"""

JS = """
const BOLUMLER = __BOLUMLER__;
const q = s => document.querySelector(s);
const ilerle = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
const yum = x => 1 - Math.pow(1 - x, 3);
const bolumler = [...document.querySelectorAll('.b')];
const goster = (el, d, dy) => { if (!el) return; el.style.opacity = d; el.style.transform = `translateY(${dy * (1 - d)}px)`; };
window.sigdir = function () {
  bolumler.forEach(el => { el.style.display = 'block'; });   // gizli bölümler ölçülemez
  document.querySelectorAll('.bilgi').forEach(b => {
    const h = b.querySelector('h2'), p = b.querySelector('p'); let hp = 72, pp = 42;
    while (b.scrollHeight > b.clientHeight && (hp > 50 || pp > 32)) {
      if (hp > 50) { hp -= 4; h.style.fontSize = hp + 'px'; }
      if (pp > 32) { pp -= 2; p.style.fontSize = pp + 'px'; }
    }
  });
  const g = q('.giris h1'); let px = 150; while (g.scrollWidth > g.clientWidth && px > 80) { px -= 4; g.style.fontSize = px + 'px'; }
  bolumler.forEach(el => { el.style.display = 'none'; });
};
window.kare = function (t) {
  BOLUMLER.forEach((b, i) => {
    const el = bolumler[i];
    const son = i === BOLUMLER.length - 1;
    const o = Math.min(yum(ilerle(t, b[0], b[0] + 0.45)), son ? 1 : 1 - yum(ilerle(t, b[1] - 0.35, b[1])));
    el.style.opacity = o; el.style.display = o > 0 ? 'block' : 'none';
    if (o <= 0) return;
    const img = el.querySelector('.foto img, .arka');
    if (img) img.style.transform = `scale(${1 + 0.07 * ilerle(t, b[0], b[1])})`;
    goster(el.querySelector('.ust2'), yum(ilerle(t, b[0] + 0.2, b[0] + 0.7)), 30);
    goster(el.querySelector('h2'), yum(ilerle(t, b[0] + 0.4, b[0] + 1.0)), 40);
    goster(el.querySelector('.bilgi p'), yum(ilerle(t, b[0] + 1.1, b[0] + 1.7)), 30);
    const c = el.querySelector('.cubuk i'); if (c) c.style.width = (100 * ilerle(t, b[0], b[1])) + '%';
    el.querySelectorAll('.liste span').forEach((s, k) => goster(s, yum(ilerle(t, b[0] + 0.9 + k * 0.25, b[0] + 1.3 + k * 0.25)), 20));
    const ld = el.querySelector('.kapanis img'); if (ld) ld.style.transform = `scale(${0.9 + 0.1 * yum(ilerle(t, b[0], b[0] + 1))})`;
  });
};
"""


def hazirla():
    """Haberleri seçer, sayfayı ve bölüm zamanlarını hazırlar."""
    adaylar = haftanin_haberleri()
    for h in adaylar:
        h["ozet_kisa"] = kisa_ozet(h.get("ozet"))
    secim, t = [], GIRIS
    for h in adaylar:
        d = okuma_suresi(h)
        if len(secim) < 6 and t + d + KAPANIS <= EN_FAZLA:
            secim.append(h)
            t += d
    if len(secim) < 3:
        return None
    secim.sort(key=lambda h: h["tarih"])  # haftanın akışına göre: eskiden yeniye

    logo = bot.veri_uri(os.path.join(bot.KOK, "assets", "logo-beyaz.png"), "image/png")
    son = dt.datetime.now()
    bas = son - dt.timedelta(days=6)
    aralik = (f"{bas.day}–{son.day} {bot.AYLAR[son.month - 1]} {son.year}" if bas.month == son.month
              else f"{bas.day} {bot.AYLAR[bas.month - 1]} – {son.day} {bot.AYLAR[son.month - 1]} {son.year}")
    once, sonra = (BASLIK.split("|", 1) + [""])[:2]
    ki = E(bot.KI_ETIKET)
    ust = lambda sag: (f'<div class="ust"><img src="{logo}" alt="Havadis.at"><div class="sag">'
                       f'<div class="etiket kos">{sag}</div><div class="ki">{ki}</div></div></div>')

    bolumler, govde, t = [(0.0, GIRIS)], [], GIRIS
    liste = "".join(f'<span><b>{i + 1:02d}</b>{E(bot.kisalt(h["baslik"], 46))}</span>' for i, h in enumerate(secim))
    govde.append(f'<div class="b"><img class="arka" src="{foto(secim[-1]["resim"], W, H)}" alt=""><div class="karart"></div>'
                 f'{ust("HAFTALIK ÖZET")}<div class="giris"><h1 class="kos">{E(once)}<br><span class="bant">{E(sonra)}</span></h1>'
                 f'<div class="aralik kos">{aralik.upper()}</div><div class="liste">{liste}</div></div></div>')
    n = len(secim)
    for i, h in enumerate(secim):
        d = okuma_suresi(h)
        bolumler.append((t, t + d))
        t += d
        tr = h["tarih"]
        govde.append(f'<div class="b">{ust(f"{i + 1:02d} / {n:02d}")}<div class="cubuk"><i></i></div>'
                     f'<div class="foto"><img src="{foto(h["resim"], 1080, 620)}" alt=""></div>'
                     f'<div class="bilgi"><div class="ust2 kos"><span class="no">{i + 1:02d}</span>'
                     f'<span class="gun">{karusel.GUNLER[tr.weekday()]} · {tr.day} {bot.AYLAR[tr.month - 1]}</span>'
                     f'<span class="kat">{E(h["kategori"])}</span></div>'
                     f'<h2 class="kos">{E(h["baslik"])}</h2><p>{E(h["ozet_kisa"])}</p></div></div>')
    bolumler.append((t, t + KAPANIS))
    govde.append(f'<div class="b"><div class="kapanis"><img src="{logo}" alt="Havadis.at">'
                 f'<div class="cta kos">Haberlerin tamamı<br><span class="bant">havadis.at’de</span></div>'
                 f'<div class="takip">Her pazar haftanın özeti<small>Takip edin · Abone olun: @havadis.at</small></div></div></div>')
    sure = round(t + KAPANIS, 2)
    js = JS.replace("__BOLUMLER__", json.dumps(bolumler))
    sayfa = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8">{karusel.FONT}<style>{CSS}</style></head>'
             f'<body><div class="v">{"".join(govde)}</div><script>{js}</script></body></html>')
    return {"haberler": secim, "sure": sure, "bolumler": bolumler, "sayfa": sayfa, "aralik": aralik}


def video_uret(veri, cikti):
    muzik = os.path.splitext(cikti)[0] + "-muzik.wav"
    muzik_uret.uret(muzik, veri["sure"], gecisler=[b[0] for b in veri["bolumler"][1:]])
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-i", muzik, "-t", str(veri["sure"]), "-c:v", "libx264", "-preset", "medium", "-crf", "22",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        s = tarayici.new_page(viewport={"width": W, "height": H})
        s.set_content(veri["sayfa"], wait_until="networkidle", timeout=120000)
        s.evaluate("document.fonts.ready")
        s.evaluate("() => window.sigdir()")
        for i in range(int(veri["sure"] * FPS)):
            s.evaluate(f"() => window.kare({i / FPS})")
            ffmpeg.stdin.write(s.screenshot(type="jpeg", quality=88))
        tarayici.close()
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError("ffmpeg haftalık özet videosunu oluşturamadı")
    kapak = os.path.splitext(cikti)[0] + "-kapak.jpg"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2.8", "-i", cikti, "-frames:v", "1", "-q:v", "2", kapak],
                   check=True)
    return cikti, kapak


def ozet_saati_mi():
    return bot.ELLE or bot.viyana_saati() == 11


def calistir():
    os.makedirs(bot.CIKTI, exist_ok=True)
    d = karusel.durum_oku()
    d.setdefault("ozet_video", [])
    simdi = dt.datetime.now()
    hafta = f"{simdi.isocalendar().year}-H{simdi.isocalendar().week:02d}"
    if hafta in d["ozet_video"] and not bot.DRY_RUN:
        bot.log("Bu haftanın özet videosu zaten paylaşıldı.")
        return 0
    veri = hazirla()
    if not veri:
        bot.log("Haftalık özet videosu için yeterli haber yok.")
        return 0
    for i, h in enumerate(veri["haberler"]):
        bot.log(f"{i + 1}. {h['kategori']} | {h['baslik']} | fotoğraf: {h['resim'].rsplit('/', 1)[-1]}")
    video, kapak = video_uret(veri, os.path.join(bot.CIKTI, f"ozet-{hafta}.mp4"))
    bot.log(f"Haftalık özet videosu hazır: {video} ({veri['sure']:.0f} sn, {len(veri['haberler'])} haber)")

    maddeler = "\n".join(f"{i + 1}. {h['baslik']}" for i, h in enumerate(veri["haberler"]))
    linkler = "\n".join(f"{i + 1}. {h['link']}" for i, h in enumerate(veri["haberler"]))
    ki = f"\n\n🤖 {bot.KI_ETIKET}" if bot.KI_ETIKET else ""
    giris = f"Avusturya'da bu hafta 📍 {veri['aralik']}\n\n{maddeler}"
    fb_metin = f"{giris}\n\n👉 Haberlerin tamamı:\n{linkler}{ki}\n\n#havadis #Avusturya #Vorarlberg #haftanınözeti"
    ig_metin = (f"{giris}\n\n👉 Haberlerin tamamı havadis.at'de (link profilimizde){ki}"
                f"\n\n#havadis #Avusturya #Vorarlberg #haftanınözeti #gurbetçi")
    yt_aciklama = (f"{giris}\n\nHer pazar Avusturya ve Vorarlberg'den haftanın öne çıkan haberleri. "
                   f"Abone olun, haftanın özetini kaçırmayın.\n\n👉 Haberlerin tamamı:\n{linkler}{ki}"
                   f"\n\n#havadis #Avusturya #Shorts")
    if bot.DRY_RUN:
        bot.log("DENEME MODU: haftalık özet videosu paylaşılmadı.")
        return 0

    kayit = {"tur": "ozet_video", "hafta": hafta, "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    def dene(ad, is_):
        try:
            kayit[ad] = is_()
            bot.log(f"{ad} paylaşıldı:", kayit[ad])
        except Exception as e:
            kayit[f"{ad}_hata"] = str(e)[:300]
            bot.log(f"{ad} hatası:", e)
            bot.gh_hata(f"Haftalık özet – {ad} hatası", e)

    dene("facebook_reel", lambda: bot.facebook_reel(video, fb_metin, kapak))
    if bot.IG_USER_ID:
        dene("instagram_reel", lambda: bot.instagram_video(video, "REELS", ig_metin))
    import youtube
    if youtube.hazir_mi():
        dene("youtube", lambda: youtube.yukle(video, f"Avusturya'da bu hafta | {veri['aralik']}", yt_aciklama,
                                              ["havadis", "Avusturya", "Vorarlberg", "haber", "haftalık özet"]))
    if any(k in kayit for k in ("facebook_reel", "instagram_reel", "youtube")):
        d["ozet_video"].append(hafta)
        karusel.durum_yaz(d)
        return 0
    raise RuntimeError("Haftalık özet videosu hiçbir platformda paylaşılamadı.")


if __name__ == "__main__":
    v = hazirla()
    if not v:
        sys.exit("Yeterli haber yok.")
    for i, h in enumerate(v["haberler"]):
        print(f"{i + 1}. {h['kategori']} | {h['baslik']}")
    print(video_uret(v, sys.argv[1] if len(sys.argv) > 1 else "ozet.mp4"), f"{v['sure']:.1f} sn")
