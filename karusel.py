#!/usr/bin/env python3
"""Karusel paylaşımları:
  - Haftalık özet: "Vorarlberg'de bu hafta" (koyu tasarım, kapak + 4 haber), pazar akşamı
  - Rehber: "Bilmeniz gerekenler" (açık tasarım, siyah logo), onaylanmış içerik dosyalarından, çarşamba akşamı
"""
import datetime as dt
import glob
import html
import json
import os
from io import BytesIO

from PIL import Image

import havadis_bot as bot

E = html.escape
DURUM = os.path.join(bot.KOK, "karusel_durum.json")
REHBER_KLASORU = os.path.join(bot.KOK, "rehber")
GUNLER = ["PAZARTESİ", "SALI", "ÇARŞAMBA", "PERŞEMBE", "CUMA", "CUMARTESİ", "PAZAR"]

ORTAK_CSS = """
  html, body { margin: 0; padding: 0; }
  body { width: 1080px; height: 1350px; overflow: hidden; }
  .s { position: relative; width: 1080px; height: 1350px; overflow: hidden; box-sizing: border-box;
       font-family: 'Barlow', Arial, sans-serif; }
  .kos { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; }
  .ust { position: absolute; left: 64px; right: 64px; top: 64px; display: flex; justify-content: space-between;
         align-items: center; z-index: 3; }
  .ust img { width: 230px; height: auto; display: block; }
  .etiket { font-family: 'Barlow Condensed', sans-serif; font-size: 26px; font-weight: 800; letter-spacing: 3px;
            padding: 8px 18px; background: #E42320; color: #fff; text-transform: uppercase; }
  .alt { position: absolute; left: 64px; right: 64px; bottom: 64px; display: flex; justify-content: space-between;
         align-items: center; padding-top: 22px; z-index: 3; }
  .alt .site { font-size: 26px; font-weight: 600; }
  .alt .ki { display: block; font-size: 18px; font-weight: 500; margin-top: 4px; opacity: .7; }
  .alt .ki:empty { display: none; }
  .alt .sag { font-family: 'Barlow Condensed', sans-serif; font-size: 28px; font-weight: 700; letter-spacing: 2px;
              text-transform: uppercase; }
  .bant { background: #E42320; color: #fff; padding: 0 14px; -webkit-box-decoration-break: clone;
          box-decoration-break: clone; }
"""
FONT = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:'
        'wght@700;800;900&family=Barlow:wght@500;600;700;800&display=swap">')


def sayfa(govde, css, sigdir_js=""):
    return (f'<!doctype html><html lang="tr"><head><meta charset="utf-8">{FONT}<style>{ORTAK_CSS}{css}</style>'
            f'</head><body>{govde}<script>window.sigdir=function(){{{sigdir_js}}};</script></body></html>')


def foto_uri(bayt, w, h):
    foto = Image.open(BytesIO(bayt)).convert("RGB")
    oran = max(w / foto.width, h / foto.height)
    foto = foto.resize((round(foto.width * oran), round(foto.height * oran)), Image.LANCZOS)
    x, y = (foto.width - w) // 2, int((foto.height - h) * 0.35)
    t = BytesIO()
    foto.crop((x, y, x + w, y + h)).save(t, "JPEG", quality=90)
    return bot.veri_uri(t.getvalue(), "image/jpeg")


def alt_satir(sag):
    return (f'<div class="alt"><div class="site">havadis.at<span class="ki">{E(bot.KI_ETIKET)}</span></div>'
            f'<div class="sag">{sag}</div></div>')


# ------------------------------------------------------------------ Haftalık özet (koyu)

HAFTA_CSS = """
  .s { background: #070B14; color: #fff; }
  .arka { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .karart { position: absolute; inset: 0; background: linear-gradient(rgba(7,11,20,.80), rgba(7,11,20,.92) 45%, #070B14); }
  .kapak-baslik { position: absolute; left: 64px; right: 64px; top: 210px; }
  .kapak-baslik h1 { margin: 22px 0 0; font-size: 150px; line-height: .95; font-weight: 900; text-transform: uppercase; }
  .tarih-araligi { margin-top: 24px; font-size: 36px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.85); }
  .liste { position: absolute; left: 64px; right: 64px; top: 720px; display: flex; flex-direction: column; }
  .liste .m { display: flex; gap: 24px; align-items: baseline; padding: 20px 0; border-top: 1px solid rgba(255,255,255,.2); }
  .liste .no { font-size: 52px; font-weight: 900; color: #E42320; width: 70px; flex: none; }
  .liste .b { font-size: 32px; font-weight: 700; line-height: 1.25; display: -webkit-box; -webkit-line-clamp: 2;
              -webkit-box-orient: vertical; overflow: hidden; }
  .alt { border-top: 1px solid rgba(255,255,255,.25); }
  .foto-ust { position: absolute; left: 0; top: 0; width: 1080px; height: 660px; object-fit: cover; }
  .foto-golge { position: absolute; left: 0; right: 0; top: 0; height: 680px;
                background: linear-gradient(rgba(7,11,20,.55), rgba(7,11,20,0) 30%, rgba(7,11,20,0) 60%, #070B14); }
  .icerik { position: absolute; left: 64px; right: 64px; top: 600px; bottom: 170px; display: flex; flex-direction: column; gap: 22px; }
  .numara { display: flex; align-items: baseline; gap: 6px; }
  .numara b { font-size: 130px; line-height: .8; font-weight: 900; color: #E42320; }
  .numara span { font-size: 44px; font-weight: 800; color: rgba(255,255,255,.5); }
  .gun { font-size: 26px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.75); }
  .icerik h2 { margin: 0; font-size: 80px; line-height: 1; font-weight: 900; text-transform: uppercase; }
  .icerik p { margin: 0; font-size: 33px; line-height: 1.35; font-weight: 500; color: #E4E8EF; }
"""
HAFTA_SIGDIR = """
  const kb = document.querySelector('.kapak-baslik h1');
  if (kb) { let px = 150; while (kb.scrollWidth > kb.clientWidth && px > 90) { px -= 4; kb.style.fontSize = px + 'px'; } return; }
  const ic = document.querySelector('.icerik'); if (!ic) return;
  const h = ic.querySelector('h2'), p = ic.querySelector('p');
  let px = 80; while (ic.scrollHeight > ic.clientHeight && px > 52) { px -= 4; h.style.fontSize = px + 'px'; }
  let k = p.textContent.trim().split(/\\s+/);
  while (ic.scrollHeight > ic.clientHeight && k.length) { k.pop(); p.textContent = k.length ? k.join(' ') + '…' : ''; }
"""


def tarih_metni(t):
    return f"{t.day} {bot.AYLAR[t.month - 1]}"


def haftalik_slaytlar(haberler, fotolar, bas, son):
    logo = bot.veri_uri(os.path.join(bot.KOK, "assets", "logo-beyaz.png"), "image/png")
    ust = f'<div class="ust"><img src="{logo}" alt="Havadis.at"><div class="etiket">Haftalık özet</div></div>'
    aralik = (f"{bas.day}–{son.day} {bot.AYLAR[son.month - 1]} {son.year}" if bas.month == son.month
              else f"{tarih_metni(bas)} – {tarih_metni(son)} {son.year}")
    liste = "".join(f'<div class="m"><div class="no kos">0{i + 1}</div><div class="b">{E(h["baslik"])}</div></div>'
                    for i, h in enumerate(haberler))
    kapak = (f'<div class="s"><img class="arka" src="{foto_uri(fotolar[0], 1080, 1350)}" alt=""><div class="karart"></div>{ust}'
             f'<div class="kapak-baslik"><h1 class="kos">Vorarlberg’de<br><span class="bant">bu hafta</span></h1>'
             f'<div class="tarih-araligi kos">{aralik.upper()}</div></div>'
             f'<div class="liste">{liste}</div>{alt_satir("Kaydır →")}</div>')
    slaytlar = [sayfa(kapak, HAFTA_CSS, HAFTA_SIGDIR)]
    for i, (h, f) in enumerate(zip(haberler, fotolar)):
        t = h["tarih"]
        govde = (f'<div class="s"><img class="foto-ust" src="{foto_uri(f, 1080, 660)}" alt=""><div class="foto-golge"></div>{ust}'
                 f'<div class="icerik"><div class="numara kos"><b>0{i + 1}</b><span>/0{len(haberler)}</span></div>'
                 f'<div class="gun kos">{GUNLER[t.weekday()]} · {tarih_metni(t)}</div>'
                 f'<h2 class="kos">{E(h["baslik"])}</h2><p>{E(h.get("ozet", ""))}</p></div>'
                 f'{alt_satir("Haberin tamamı havadis.at’de →")}</div>')
        slaytlar.append(sayfa(govde, HAFTA_CSS, HAFTA_SIGDIR))
    return slaytlar


def haftanin_haberleri(adet=4, kategori="vorarlberg"):
    """Arşivden son 7 günün haberlerini seçer: mümkünse her günden bir haber, en yeniden geriye."""
    simdi = dt.datetime.now(dt.timezone.utc)
    arsiv = bot.arsiv_oku()
    adaylar = []
    for h in arsiv:
        t = dt.datetime.fromisoformat(h["tarih"]) if h.get("tarih") else None
        if t and (simdi - t).days < 7 and h["kategori"].casefold() == kategori and h.get("resim"):
            adaylar.append(dict(h, tarih=t))
    adaylar.sort(key=lambda h: h["tarih"], reverse=True)
    secilen, gunler = [], set()
    for h in adaylar:                       # önce her günden bir haber
        if h["tarih"].date() not in gunler:
            secilen.append(h); gunler.add(h["tarih"].date())
        if len(secilen) == adet:
            break
    for h in adaylar:                       # yetmezse kalanlarla tamamla
        if len(secilen) == adet:
            break
        if h not in secilen:
            secilen.append(h)
    return sorted(secilen, key=lambda h: h["tarih"])


# ------------------------------------------------------------------ Rehber (açık)

REHBER_CSS = """
  .s { background: #F5F3EF; color: #0B0B0B; }
  .alt { border-top: 2px solid #0B0B0B; }
  .alt .sag { color: #0B0B0B; }
  .kapak-icerik { position: absolute; left: 64px; right: 64px; top: 230px; bottom: 170px; display: flex;
                  flex-direction: column; justify-content: center; gap: 36px; }
  .kapak-icerik h1 { margin: 0; font-size: 140px; line-height: .98; font-weight: 900; text-transform: uppercase; }
  .kapak-icerik .alt-baslik { font-size: 42px; line-height: 1.3; font-weight: 600; color: #3A3A3A; }
  .kapak-icerik .kaydet { align-self: flex-start; font-size: 30px; font-weight: 700; color: #C81D17;
                          border: 3px solid #C81D17; padding: 12px 22px; }
  .sayfa-icerik { position: absolute; left: 64px; right: 64px; top: 200px; bottom: 170px; display: flex;
                  flex-direction: column; gap: 34px; }
  .sayfa-icerik .bas { display: flex; align-items: baseline; gap: 26px; }
  .sayfa-icerik .bas b { font-size: 120px; line-height: .8; font-weight: 900; color: #E42320; }
  .sayfa-icerik h2 { margin: 0; font-size: 76px; line-height: 1; font-weight: 900; text-transform: uppercase; }
  .sayfa-icerik ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 26px; }
  .sayfa-icerik li { position: relative; padding-left: 44px; font-size: 36px; line-height: 1.35; font-weight: 500; }
  .sayfa-icerik li::before { content: ""; position: absolute; left: 0; top: 16px; width: 18px; height: 18px; background: #E42320; }
  .sayfa-icerik li strong { font-weight: 800; }
  .not { font-size: 26px; line-height: 1.4; color: #4A4A4A; border-left: 6px solid #E42320; padding-left: 22px; }
  .sayfa-no { font-family: 'Barlow Condensed', sans-serif; font-size: 28px; font-weight: 800; letter-spacing: 2px; color: #6A6A6A; }
"""
REHBER_SIGDIR = """
  const ic = document.querySelector('.sayfa-icerik, .kapak-icerik'); if (!ic) return;
  const h = ic.querySelector('h1, h2'); const lis = ic.querySelectorAll('li');
  let px = parseFloat(getComputedStyle(h).fontSize), lp = 36;
  while (h.scrollWidth > h.clientWidth && px > 56) { px -= 4; h.style.fontSize = px + 'px'; }
  while (ic.scrollHeight > ic.clientHeight && (px > 56 || lp > 26)) {
    if (px > 56) { px -= 4; h.style.fontSize = px + 'px'; }
    if (lp > 26) { lp -= 1; lis.forEach(l => l.style.fontSize = lp + 'px'); }
  }
"""


def rehber_slaytlar(r):
    logo = bot.veri_uri(os.path.join(bot.KOK, "assets", "logo-siyah.png"), "image/png")
    ust = f'<div class="ust"><img src="{logo}" alt="Havadis.at"><div class="etiket">Bilmeniz gerekenler</div></div>'
    toplam = len(r["sayfalar"]) + 2
    guncel = "Güncel: " + E(r["guncel"])
    kapak = (f'<div class="s">{ust}<div class="kapak-icerik">'
             f'<h1 class="kos">{E(r["baslik_beyaz"])}<br><span class="bant" lang="{r.get("vurgu_dil", "tr")}">'
             f'{E(r["baslik_vurgu"])}</span></h1>'
             f'<div class="alt-baslik">{E(r["alt_baslik"])}</div>'
             f'<div class="kaydet">Kaydedin, lazım olur →</div></div>'
             f'{alt_satir(guncel)}</div>')
    slaytlar = [sayfa(kapak, REHBER_CSS, REHBER_SIGDIR)]
    for i, sy in enumerate(r["sayfalar"]):
        maddeler = "".join(f"<li>{m}</li>" for m in sy["maddeler"])  # maddelerde <strong> kullanılabilir
        govde = (f'<div class="s">{ust}<div class="sayfa-icerik"><div class="bas"><b class="kos">0{i + 1}</b>'
                 f'<h2 class="kos">{E(sy["baslik"])}</h2></div><ul>{maddeler}</ul></div>'
                 f'{alt_satir(f"<span class=sayfa-no>{i + 2}/{toplam}</span>")}</div>')
        slaytlar.append(sayfa(govde, REHBER_CSS, REHBER_SIGDIR))
    son = (f'<div class="s">{ust}<div class="sayfa-icerik"><div class="bas"><h2 class="kos">Önemli <span class="bant">not</span></h2></div>'
           f'<div class="not">Bu sayfalar genel bilgilendirme amaçlıdır; kişisel durumunuz için ilgili kurumdan bilgi alın. '
           f'Tutarlar ve kurallar değişebilir.</div>'
           f'<ul><li><strong>Kaynak:</strong> {E(r["kaynak"])}</li>'
           f'<li><strong>Güncelleme:</strong> {E(r["guncel"])}</li>'
           f'<li>Kaydedin ve ihtiyacı olan biriyle paylaşın.</li>'
           f'<li>Daha fazla rehber için <strong>@havadis.at</strong>’i takip edin.</li></ul></div>'
           f'{alt_satir(f"<span class=sayfa-no>{toplam}/{toplam}</span>")}</div>')
    slaytlar.append(sayfa(son, REHBER_CSS, REHBER_SIGDIR))
    return slaytlar


def siradaki_rehber(yayinlananlar):
    """Onaylanmış ve henüz yayınlanmamış ilk rehber (dosya adı sırasına göre)."""
    for yol in sorted(glob.glob(os.path.join(REHBER_KLASORU, "*.json"))):
        r = json.load(open(yol, encoding="utf-8"))
        if r.get("durum") == "onaylandi" and r["id"] not in yayinlananlar:
            return r
    return None


# ------------------------------------------------------------------ Çizim ve paylaşım

def ciz(slaytlar, klasor, onek):
    from playwright.sync_api import sync_playwright
    yollar = []
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        s = tarayici.new_page(viewport={"width": 1080, "height": 1350})
        for i, html_ in enumerate(slaytlar):
            s.set_content(html_, wait_until="networkidle", timeout=60000)
            s.evaluate("document.fonts.ready")
            s.evaluate("() => window.sigdir && window.sigdir()")
            yol = os.path.join(klasor, f"{onek}-{i + 1}.jpg")
            Image.open(BytesIO(s.screenshot())).convert("RGB").save(yol, "JPEG", quality=92)
            yollar.append(yol)
        tarayici.close()
    return yollar


def facebook_coklu(gorseller, metin):
    """Facebook: fotoğrafları yayınlamadan yükler, tek gönderide birleştirir. Instagram için görsel adreslerini döndürür."""
    idler, adresler = [], []
    for g in gorseller:
        with open(g, "rb") as f:
            r = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.PAGE_ID}/photos"), timeout=120,
                                          data={"published": "false", "access_token": bot.PAGE_TOKEN},
                                          files={"source": ("s.jpg", f, "image/jpeg")}))
        idler.append(r["id"])
        bilgi = bot.kontrol(bot.HTTP.get(bot.graph(r["id"]), timeout=30,
                                         params={"fields": "images", "access_token": bot.PAGE_TOKEN}))
        adresler.append(max(bilgi["images"], key=lambda i: i["width"])["source"])
    veri = {"message": metin, "access_token": bot.PAGE_TOKEN}
    for i, pid in enumerate(idler):
        veri[f"attached_media[{i}]"] = json.dumps({"media_fbid": pid})
    gonderi = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.PAGE_ID}/feed"), data=veri, timeout=60))
    return gonderi["id"], adresler


def instagram_karusel(adresler, metin):
    cocuklar = []
    for a in adresler:
        k = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
            "image_url": a, "is_carousel_item": "true", "access_token": bot.PAGE_TOKEN}))
        bot.ig_bekle(k["id"])
        cocuklar.append(k["id"])
    kap = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media"), timeout=60, data={
        "media_type": "CAROUSEL", "children": ",".join(cocuklar), "caption": metin, "access_token": bot.PAGE_TOKEN}))
    bot.ig_bekle(kap["id"])
    yayin = bot.kontrol(bot.HTTP.post(bot.graph(f"{bot.IG_USER_ID}/media_publish"), timeout=60,
                                      data={"creation_id": kap["id"], "access_token": bot.PAGE_TOKEN}))
    return yayin["id"]


def durum_oku():
    return json.load(open(DURUM, encoding="utf-8")) if os.path.exists(DURUM) else {"haftalik": [], "rehber": []}


def durum_yaz(d):
    json.dump(d, open(DURUM, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def paylas(gorseller, fb_metin, ig_metin, kayit):
    fb_id, adresler = facebook_coklu(gorseller, fb_metin)
    kayit["facebook"] = fb_id
    bot.log("Facebook karuseli paylaşıldı:", fb_id)
    if bot.IG_USER_ID:
        try:
            kayit["instagram"] = instagram_karusel(adresler, ig_metin)
            bot.log("Instagram karuseli paylaşıldı:", kayit["instagram"])
        except Exception as e:
            kayit["instagram_hata"] = str(e)[:300]
            bot.gh_hata("Instagram karusel hatası", e)


def haftalik_calistir():
    os.makedirs(bot.CIKTI, exist_ok=True)
    d = durum_oku()
    simdi = dt.datetime.now()
    hafta = f"{simdi.isocalendar().year}-H{simdi.isocalendar().week:02d}"
    if hafta in d["haftalik"] and not bot.DRY_RUN:
        bot.log("Bu haftanın özeti zaten paylaşıldı.")
        return 0
    haberler = haftanin_haberleri()
    if len(haberler) < 3:
        bot.log("Haftalık özet için yeterli Vorarlberg haberi yok:", len(haberler))
        return 0
    fotolar = []
    for h in haberler:
        r = bot.HTTP.get(h["resim"], timeout=60); r.raise_for_status(); fotolar.append(r.content)
    son = dt.datetime.now()
    bas = son - dt.timedelta(days=6)  # kapakta son 7 gün
    gorseller = ciz(haftalik_slaytlar(haberler, fotolar, bas, son), bot.CIKTI, f"haftalik-{hafta}")
    bot.log("Haftalık özet görselleri hazır:", len(gorseller))
    maddeler = "\n".join(f"{i + 1}. {h['baslik']}" for i, h in enumerate(haberler))
    ki = f"\n\n🤖 {bot.KI_ETIKET}" if bot.KI_ETIKET else ""
    fb_linkler = "\n".join(f"{i + 1}. {h['link']}" for i, h in enumerate(haberler))
    ig_metin = (f"Vorarlberg'de bu hafta 📍 Haftanın öne çıkan haberleri:\n\n{maddeler}\n\n"
                f"👉 Haberlerin tamamı havadis.at'de (link profilimizde){ki}\n\n#Vorarlberg #havadis #haftanınözeti #Avusturya")
    fb_metin = (f"Vorarlberg'de bu hafta 📍 Haftanın öne çıkan haberleri:\n\n{maddeler}\n\n"
                f"👉 Haberlerin tamamı:\n{fb_linkler}{ki}\n\n#Vorarlberg #havadis #Avusturya")
    if bot.DRY_RUN:
        bot.log("DENEME MODU: haftalık özet paylaşılmadı.")
        return 0
    kayit = {"tur": "haftalik", "hafta": hafta, "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    paylas(gorseller, fb_metin, ig_metin, kayit)
    d["haftalik"].append(hafta)
    durum_yaz(d)
    return 0


def rehber_calistir():
    os.makedirs(bot.CIKTI, exist_ok=True)
    d = durum_oku()
    r = siradaki_rehber(d["rehber"])
    if not r:
        bot.log("Onaylanmış, yayınlanmamış rehber yok.")
        return 0
    gorseller = ciz(rehber_slaytlar(r), bot.CIKTI, f"rehber-{r['id']}")
    bot.log("Rehber görselleri hazır:", r["id"], len(gorseller))
    ki = f"\n\n🤖 {bot.KI_ETIKET}" if bot.KI_ETIKET else ""
    metin = f"{r['metin']}\n\n🔖 Kaydedin, lazım olur. Kaynak: {r['kaynak']}{ki}\n\n{r.get('hashtagler', '#havadis #Avusturya')}"
    if bot.DRY_RUN:
        bot.log("DENEME MODU: rehber paylaşılmadı.")
        return 0
    kayit = {"tur": "rehber", "id": r["id"], "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    paylas(gorseller, metin, metin, kayit)
    d["rehber"].append(r["id"])
    durum_yaz(d)
    return 0
