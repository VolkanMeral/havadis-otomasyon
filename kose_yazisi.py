#!/usr/bin/env python3
"""Köşe yazısı paylaşımı: havadis.at'teki bir köşe yazısını görselle paylaşır.
Facebook: görsel + açıklamada sadece yazının linki.  Instagram: görsel + yazının tam metni (2200 karakter sınırı).

Kullanım:  python kose_yazisi.py <yazı adresi> [--paylas]
--paylas yoksa sadece önizleme üretir: ornek/kose/<id>/ (gorsel.jpg, instagram.txt, facebook.txt)"""
import html as H
import os
import re
import string
import sys
from io import BytesIO

from PIL import Image

import havadis_bot as bot

IG_SINIR = 2200
TARAYICI = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/130.0 Safari/537.36", "Accept-Language": "tr-TR,tr;q=0.9"}


def temiz(parca):
    parca = re.sub(r"<br\s*/?>", "\n", parca, flags=re.I)
    parca = re.sub(r"<[^>]+>", "", parca)
    return re.sub(r"[ \t\r\f\v]+", " ", H.unescape(parca)).strip()


def meta(sayfa, ad):
    m = re.search(rf'<meta[^>]+(?:property|name)=["\']{ad}["\'][^>]*content=["\']([^"\']*)', sayfa, re.I) or \
        re.search(rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:property|name)=["\']{ad}["\']', sayfa, re.I)
    return H.unescape(m.group(1)).strip() if m else ""


def yazi_oku(adres):
    r = bot.HTTP.get(adres, timeout=60, headers=TARAYICI)
    r.raise_for_status()
    sayfa = r.content.decode("utf-8", errors="replace")
    baslik = meta(sayfa, "og:title") or temiz((re.search(r"<h1[^>]*>(.*?)</h1>", sayfa, re.S) or [None, ""])[1])
    resim = meta(sayfa, "og:image")
    yazar = meta(sayfa, "author") or meta(sayfa, "article:author")
    # Başlık çoğu zaman "Başlık - Yazar Adı - Havadis Haber" biçiminde
    parcalar = [x.strip() for x in re.split(r"\s+-\s+", baslik)]
    if parcalar and parcalar[-1].lower().startswith("havadis"):
        parcalar = parcalar[:-1]
    if len(parcalar) >= 2:
        yazar = yazar or parcalar[-1]
        baslik = " - ".join(parcalar[:-1])
    # Metin: en çok paragraf içeren blok
    paragraflar = [temiz(p) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", sayfa, re.S | re.I)]
    paragraflar = [p for p in paragraflar if len(p) > 40 and "©" not in p and "çerez" not in p.lower()]
    return {"adres": adres, "baslik": baslik, "resim": resim, "yazar": yazar, "paragraflar": paragraflar,
            "ham": sayfa}


def instagram_metni(y):
    bas = f"✍️ {y['yazar']} yazdı:\n{y['baslik']}\n\n" if y["yazar"] else f"{y['baslik']}\n\n"
    son = "\n\n#havadis #köşeyazısı #Avusturya #gündem"
    devam = "…\n\n📰 Yazının devamı www.havadis.at web sitemizde"
    govde = ""
    for p in y["paragraflar"]:
        aday = (govde + "\n\n" + p) if govde else p
        if len(bas + aday + son) > IG_SINIR:
            # sığmayan paragrafı cümle sınırından kes
            kalan = IG_SINIR - len(bas + govde + devam + son) - 2
            if kalan > 120:
                kes = p[:kalan].rsplit(". ", 1)[0] + "."
                govde = (govde + "\n\n" + kes) if govde else kes
            if govde.rstrip()[-1:] in ".!?…":
                return bas + govde + devam.lstrip("…") + son
            return bas + govde + devam + son
        govde = aday
    return bas + govde + son


SABLON = """<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Barlow:wght@500;600;700&display=swap">
<style>
 html,body{margin:0}
 .kart{width:1080px;height:1350px;position:relative;overflow:hidden;background:#070B14;color:#fff;font-family:Barlow,sans-serif}
 .zemin{position:absolute;inset:0;background:radial-gradient(circle at 80% 18%,#E4232033 0,#070B1400 45%),linear-gradient(#0d1322,#070B14)}
 .ust{position:absolute;left:72px;right:72px;top:70px;display:flex;justify-content:space-between;align-items:center}
 .ust img{height:58px}
 .tarih{font-family:'Barlow Condensed';font-weight:700;font-size:26px;letter-spacing:3px;color:rgba(255,255,255,.8)}
 .etiket{position:absolute;left:72px;top:250px;background:#E42320;font-family:'Barlow Condensed';font-weight:800;
   font-size:32px;letter-spacing:4px;padding:8px 20px}
 .foto{position:absolute;right:72px;top:220px;width:300px;height:300px;border-radius:50%;object-fit:cover;
   border:8px solid #E42320;box-shadow:0 20px 60px #0008}
 .yazar{position:absolute;left:72px;top:330px;width:560px}
 .yazar .ad{font-family:'Barlow Condensed';font-weight:900;font-size:64px;line-height:1;text-transform:uppercase}
 .yazar .alt{font-size:28px;color:rgba(255,255,255,.7);margin-top:10px}
 .tirnak{position:absolute;left:58px;top:560px;font-family:Georgia,serif;font-size:260px;line-height:1;color:#E42320}
 h1{position:absolute;left:72px;right:72px;top:700px;margin:0;font-family:'Barlow Condensed';font-weight:900;
   font-size:$px;line-height:1.02;text-transform:uppercase}
 .giris{position:absolute;left:72px;right:72px;bottom:190px;font-size:32px;line-height:1.35;color:#E4E8EF;
   border-left:8px solid #E42320;padding-left:28px}
 .alt-cizgi{position:absolute;left:72px;right:72px;bottom:72px;display:flex;justify-content:space-between;align-items:center;
   padding-top:24px;border-top:1px solid rgba(255,255,255,.25)}
 .alt-cizgi .site{font-size:26px;font-weight:600;color:rgba(255,255,255,.85)}
 .alt-cizgi .oku{font-size:27px;font-weight:500;color:rgba(255,255,255,.85)}
 .alt-cizgi .oku b{color:#FF3B36;font-weight:800}
</style></head><body><div class="kart"><div class="zemin"></div>
<div class="ust"><img src="$logo"><div class="tarih">$tarih</div></div>
<div class="etiket">KÖŞE YAZISI</div>
<img class="foto" src="$foto">
<div class="yazar"><div class="ad">$yazar</div><div class="alt">Havadis.at yazarı</div></div>
<div class="tirnak">“</div>
<h1>$baslik</h1>
<div class="giris">$giris</div>
<div class="alt-cizgi"><div class="site">havadis.at</div><div class="oku">Yazının tamamı <b>www.havadis.at</b> web sitemizde</div></div>
</div><script>
 window.sigdir=function(){const h=document.querySelector('h1'),g=document.querySelector('.giris');
   let px=parseFloat(getComputedStyle(h).fontSize);
   while(h.getBoundingClientRect().bottom>g.getBoundingClientRect().top-40&&px>44){px-=3;h.style.fontSize=px+'px';}};
</script></body></html>"""


def gorsel(y, cikti):
    import datetime as dt
    foto = BytesIO()
    if y["resim"]:
        r = bot.HTTP.get(y["resim"], timeout=60, headers=TARAYICI)
        r.raise_for_status()
        Image.open(BytesIO(r.content)).convert("RGB").save(foto, "JPEG", quality=92)
    bugun = dt.date.today()
    giris = y["paragraflar"][0] if y["paragraflar"] else ""
    sayfa = string.Template(SABLON).safe_substitute(
        logo=bot.veri_uri(os.path.join(bot.KOK, "assets", "logo-beyaz.png"), "image/png"),
        foto=bot.veri_uri(foto.getvalue(), "image/jpeg") if y["resim"] else "",
        tarih=f"{bugun.day} {bot.AYLAR[bugun.month - 1]} {bugun.year}",
        yazar=H.escape(y["yazar"]), baslik=H.escape(y["baslik"]), px="96px",
        giris=H.escape(bot.kisalt(giris, 190)))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        t = p.chromium.launch()
        s = t.new_page(viewport={"width": 1080, "height": 1350})
        s.set_content(sayfa, wait_until="networkidle", timeout=60000)
        s.evaluate("document.fonts.ready")
        s.evaluate("() => window.sigdir()")
        png = s.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        t.close()
    Image.open(BytesIO(png)).convert("RGB").save(cikti, "JPEG", quality=92)
    return cikti


if __name__ == "__main__":
    adres = sys.argv[1]
    m = re.search(r"m(\d+)\.html|ID=(\d+)", adres)
    kimlik = (m.group(1) or m.group(2)) if m else "yazi"
    if "page=makale" in adres:
        adres = f"https://www.havadis.at/makale/icerik-m{kimlik}.html"
    y = yazi_oku(adres)
    klasor = os.path.join(bot.KOK, "ornek", "kose", kimlik)
    os.makedirs(klasor, exist_ok=True)
    if not y["yazar"]:
        print("::warning title=Köşe yazısı::Yazar adı sayfada bulunamadı")
    gorsel(y, os.path.join(klasor, "gorsel.jpg"))
    ig = instagram_metni(y)
    open(os.path.join(klasor, "instagram.txt"), "w", encoding="utf-8").write(ig)
    open(os.path.join(klasor, "facebook.txt"), "w", encoding="utf-8").write(adres)
    open(os.path.join(klasor, "sayfa.html"), "w", encoding="utf-8").write(y["ham"])
    print("Başlık:", y["baslik"], "| Yazar:", y["yazar"], "| Paragraf:", len(y["paragraflar"]), "| IG metni:", len(ig))
    if "--paylas" in sys.argv:
        gorsel_yol = os.path.join(klasor, "gorsel.jpg")
        fb_id, foto_url = bot.facebook_paylas(gorsel_yol, adres)
        print("Facebook:", fb_id)
        print("Instagram:", bot.instagram_paylas(foto_url, ig))
