#!/usr/bin/env python3
"""
Havadis.at otomatik sosyal medya paylaşımı.

Her çalıştığında:
  1. havadis.at RSS akışından henüz paylaşılmamış en yeni haberi seçer
  2. Haberin fotoğrafını indirir, Havadis şablonuyla 1080x1350 kapak görseli üretir
  3. Facebook sayfasına ve Instagram hesabına Meta Graph API ile paylaşır
  4. Paylaşılan haberi posted.json dosyasına kaydeder (aynı haber iki kez paylaşılmaz)

Ayarlar ortam değişkenleriyle yapılır (README.md'ye bakın).
DRY_RUN=1 (varsayılan) iken hiçbir şey paylaşılmaz, sadece görsel ve metin üretilir.
"""
import base64
import datetime as dt
import email.utils
import html
import json
import os
import re
import string
import sys
import time
import xml.etree.ElementTree as ET
from io import BytesIO

import requests
from PIL import Image

KOK = os.path.dirname(os.path.abspath(__file__))
CIKTI = os.path.join(KOK, "cikti")
DURUM_DOSYASI = os.path.join(KOK, "posted.json")

RSS_URL = os.getenv("RSS_URL", "https://havadis.at/rss.rss")
GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v26.0")
DRY_RUN = os.getenv("DRY_RUN", "1") == "1"
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "24"))
ATLANACAK_KATEGORILER = {
    k.strip().casefold() for k in os.getenv("SKIP_CATEGORIES", "TAZİYE").split(",") if k.strip()
}
# Sadece bu kategorilerdeki haberler paylaşılır (boş bırakılırsa tüm kategoriler)
PAYLASILACAK_KATEGORILER = {
    k.strip().casefold()
    for k in os.getenv("INCLUDE_CATEGORIES", "Avusturya,Vorarlberg,Avrupa,Almanya").split(",") if k.strip()
}
# Yapay zekâ / otomasyon şeffaflık etiketi (AB Yapay Zekâ Yasası md. 50). Boş bırakılırsa eklenmez.
KI_ETIKET = os.getenv("AI_LABEL", "KI-unterstützt").strip()
SABIT_HASHTAGLER =os.getenv("BASE_HASHTAGS", "#havadis #Avusturya #haber")

def _temiz(deger, desen):
    """Kopyalarken araya giren boşluk, tırnak, satır sonu ve görünmez karakterleri temizler."""
    ham = deger or ""
    temiz = re.sub(desen, "", ham)
    return temiz, len(ham) - len(temiz)


def _id(ad):
    """ID içindeki ilk uzun rakam dizisini alır (köşeli parantez veya link yapıştırılmışsa da çalışır)."""
    m = re.search(r"\d{5,}", os.getenv(ad) or "")
    return m.group(0) if m else ""


PAGE_ID = _id("META_PAGE_ID")
IG_USER_ID = _id("IG_USER_ID")
# Meta anahtarları sadece harf ve rakamdan oluşur
PAGE_TOKEN, TOKEN_TEMIZLENEN = _temiz(os.getenv("META_PAGE_TOKEN"), r"[^A-Za-z0-9]")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")

HTTP = requests.Session()
HTTP.headers["User-Agent"] = "HavadisSosyalMedyaBot/1.0 (+https://havadis.at)"

AYLAR_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
# Kullanılacak tasarım: "kart" (sosyal gönderi kartı) veya "manset" (tam ekran manşet)
SABLON = os.getenv("TEMPLATE", "manset").strip() or "manset"
AYLAR = ["OCAK", "ŞUBAT", "MART", "NİSAN", "MAYIS", "HAZİRAN",
         "TEMMUZ", "AĞUSTOS", "EYLÜL", "EKİM", "KASIM", "ARALIK"]


def log(*a):
    print(*a, flush=True)


# ---------------------------------------------------------------- RSS

def haberleri_getir():
    """RSS'i okur. XML'in tamamı bozuk olsa bile her haberi ayrı ayrı ayıklar
    (sitedeki tek bir hatalı haber diğerlerini engellemesin diye)."""
    r = HTTP.get(RSS_URL, timeout=30)
    r.raise_for_status()
    metin = r.content.decode("utf-8", errors="replace")
    if "<item" not in metin:
        raise RuntimeError(f"RSS yerine farklı bir sayfa geldi (ilk 200 karakter): {metin[:200]!r}")
    haberler = []
    for parca in re.findall(r"<item\b[^>]*>(.*?)</item>", metin, re.S):
        def t(tag, parca=parca):
            m = re.search(rf"<{tag}\b[^>]*>(.*?)</{tag}>", parca, re.S)
            if not m:
                return ""
            deger = m.group(1).strip()
            cd = re.fullmatch(r"<!\[CDATA\[(.*?)\]\]>", deger, re.S)
            return (cd.group(1) if cd else deger).strip()
        resim = t("image")
        if not resim:
            mc = re.search(r"<media:content\b[^>]*\burl=\"([^\"]+)\"", parca)
            resim = mc.group(1) if mc else ""
        resim = html.unescape(resim)
        try:
            tarih = email.utils.parsedate_to_datetime(t("pubDate"))
        except Exception:
            tarih = None
        ozet = re.sub(r"<[^>]+>", " ", html.unescape(t("description")))
        haberler.append({
            "baslik": re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(t("title")))).strip(),
            "link": html.unescape(t("link") or t("guid")),
            "ozet": re.sub(r"\s+", " ", ozet).strip(),
            "kategori": html.unescape(t("category")) or "Haber",
            "resim": resim,
            "tarih": tarih,
        })
    return haberler


def durum_oku():
    if os.path.exists(DURUM_DOSYASI):
        with open(DURUM_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    return []


def durum_yaz(kayitlar):
    with open(DURUM_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(kayitlar[-500:], f, ensure_ascii=False, indent=1)


def haber_sec(haberler, paylasilanlar):
    linkler = {p["link"] for p in paylasilanlar}
    simdi = dt.datetime.now(dt.timezone.utc)
    adaylar = []
    for h in haberler:
        if not h["link"] or h["link"] in linkler or not h["resim"]:
            continue
        if h["kategori"].casefold() in ATLANACAK_KATEGORILER:
            continue
        if PAYLASILACAK_KATEGORILER and h["kategori"].casefold() not in PAYLASILACAK_KATEGORILER:
            continue
        if h["tarih"] and (simdi - h["tarih"]).total_seconds() > MAX_AGE_HOURS * 3600:
            continue
        adaylar.append(h)
    # En yeni haber önce
    adaylar.sort(key=lambda h: h["tarih"] or simdi, reverse=True)
    return adaylar[0] if adaylar else None


# ---------------------------------------------------------------- İçerik (başlık vurgusu + paylaşım metni)

def basit_icerik(h):
    """Yapay zekâ olmadan: başlığı ':' işaretinden böl, ikinci kısmı kırmızı bantla vurgula."""
    b = h["baslik"]
    if ":" in b:
        once, sonra = b.split(":", 1)
        beyaz, vurgu = once.strip(), sonra.strip()
    else:
        kelimeler = b.split()
        n = 2 if len(kelimeler) > 4 else 1
        beyaz, vurgu = " ".join(kelimeler[:-n]), " ".join(kelimeler[-n:])
    sayi = re.search(r"(\d[\d.,]*\s?(?:Euro|€|Avro|kişi|milyon|milyar|bin)?)", b, re.I)
    return {
        "baslik_beyaz": beyaz,
        "baslik_vurgu": vurgu,
        "ust_baslik": "",
        "etiket_ust": sayi.group(1).strip() if sayi and len(sayi.group(1).strip()) <= 11 else "",
        "etiket_alt": "",
        "ozet": h["ozet"],
        "metin": h["ozet"],
        "hashtagler": "",
    }


def claude_icerik(h):
    """ANTHROPIC_API_KEY varsa: haberi analiz edip başlık vurgusu, etiket ve paylaşım metni yazdırır."""
    istem = f"""Aşağıdaki haber için Havadis.at Instagram/Facebook gönderisi hazırla. Kurallar:
- Sadece haberde geçen bilgileri kullan, rakam veya bilgi uydurma.
- baslik_beyaz + baslik_vurgu birlikte en fazla 7 kelime, güçlü bir manşet olsun; vurgu en çarpıcı 1-3 kelime.
- ust_baslik: kategori yanındaki kısa yer/konu etiketi (örn. VORARLBERG), en fazla 2 kelime.
- etiket_ust: haberdeki en çarpıcı kısa rakam (örn. "+%35", "3.000"), yoksa boş bırak. etiket_alt: o rakamın 1-2 kelimelik açıklaması.
- ozet: görselde gösterilecek tek cümle, en fazla 110 karakter.
- metin: paylaşım açıklaması, 2-3 kısa cümle, merak uyandıran ama abartısız, en fazla 1 emoji.
- hashtagler: 4-6 Türkçe/yerel hashtag, boşlukla ayrılmış.
Yalnızca JSON döndür: {{"baslik_beyaz":"","baslik_vurgu":"","ust_baslik":"","etiket_ust":"","etiket_alt":"","ozet":"","metin":"","hashtagler":""}}

Kategori: {h['kategori']}
Başlık: {h['baslik']}
Özet: {h['ozet']}"""
    r = HTTP.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": CLAUDE_MODEL, "max_tokens": 800,
              "messages": [{"role": "user", "content": istem}]},
        timeout=60,
    )
    r.raise_for_status()
    yazi = "".join(p.get("text", "") for p in r.json().get("content", []))
    veri = json.loads(yazi[yazi.find("{"): yazi.rfind("}") + 1])
    temel = basit_icerik(h)
    temel.update({k: str(v).strip() for k, v in veri.items() if k in temel and str(v).strip()})
    return temel


def icerik_hazirla(h):
    if ANTHROPIC_API_KEY:
        try:
            return claude_icerik(h)
        except Exception as e:
            log("Claude analizi başarısız, basit moda geçiliyor:", e)
    return basit_icerik(h)


def paylasim_metni(h, ic, platform):
    kat = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", h["kategori"])
    etiketler = " ".join(dict.fromkeys((ic["hashtagler"] + " " + SABIT_HASHTAGLER + (f" #{kat}" if kat else "")).split()))
    if platform == "facebook":
        devam = f"👉 Haberin tamamı: {h['link']}"
    else:
        devam = f"👉 Haberin tamamı: {h['link']}\n(Tıklanabilir link profilimizde)"
    ki = f"\n\n🤖 {KI_ETIKET}" if KI_ETIKET else ""
    return f"{h['baslik']}\n\n{ic['metin']}\n\n{devam}{ki}\n\n{etiketler}".strip()


# ---------------------------------------------------------------- Görsel

def veri_uri(yol_veya_bayt, mime):
    bayt = yol_veya_bayt if isinstance(yol_veya_bayt, bytes) else open(yol_veya_bayt, "rb").read()
    return f"data:{mime};base64," + base64.b64encode(bayt).decode()


def kisalt(metin, n):
    """Metni kelime ortasından bölmeden n karakterle sınırlar."""
    if len(metin) <= n:
        return metin
    return metin[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def baslik_boyutu(metin):
    n = len(metin)
    if n <= 28:
        return 150
    if n <= 42:
        return 128
    if n <= 60:
        return 108
    if n <= 80:
        return 92
    return 80


def tam_ekran_hazirla(foto, w=1080, h=1350, dikey_odak=0.3):
    """Küçük fotoğrafı tam ekran için yüksek kaliteyle büyütür, kırpar ve hafifçe keskinleştirir."""
    from PIL import ImageFilter
    oran = max(w / foto.width, h / foto.height)
    yeni = foto.resize((round(foto.width * oran), round(foto.height * oran)), Image.LANCZOS)
    x = (yeni.width - w) // 2
    y = int((yeni.height - h) * dikey_odak)
    yeni = yeni.crop((x, y, x + w, y + h))
    if oran > 1.2:
        yeni = yeni.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2))
    return yeni


def gorsel_uret(h, ic, cikti_yolu):
    r = HTTP.get(h["resim"], timeout=60)
    r.raise_for_status()
    foto = Image.open(BytesIO(r.content)).convert("RGB")
    if SABLON == "manset":
        foto = tam_ekran_hazirla(foto)
    tampon = BytesIO()
    foto.save(tampon, "JPEG", quality=92)

    tarih = h["tarih"] or dt.datetime.now()
    e = html.escape
    tam_baslik = f"{ic['baslik_beyaz']} {ic['baslik_vurgu']}".strip()
    baslik_html = (e(ic["baslik_beyaz"]) + "<br>" if ic["baslik_beyaz"] else "") + \
        f'<span class="vurgu">{e(ic["baslik_vurgu"])}</span>'
    etiket_html = ""
    if ic.get("etiket_ust"):
        boy = 64 if len(ic["etiket_ust"]) <= 5 else (48 if len(ic["etiket_ust"]) <= 7 else 38)
        etiket_html = (f'<div class="etiket-yuvarlak"><b style="font-size:{boy}px">{e(ic["etiket_ust"])}</b>'
                       f'<span>{e(ic.get("etiket_alt", ""))}</span></div>')
    degerler = {
        "foto": veri_uri(tampon.getvalue(), "image/jpeg"),
        "logo": veri_uri(os.path.join(KOK, "assets", "logo-beyaz.png"), "image/png"),
        "tarih": f"{tarih.day} {AYLAR[tarih.month - 1]} {tarih.year}",
        "kategori": e(h["kategori"]),
        "ust_baslik_html": f'<div class="ust-baslik">{e(ic["ust_baslik"])}</div>' if ic.get("ust_baslik") else "",
        "baslik_html": baslik_html,
        "baslik_px": f"{baslik_boyutu(tam_baslik)}px",
        "ozet_html": f'<p class="ozet">{e(ic["ozet"])}</p>' if ic.get("ozet") else "",
        "etiket_html": etiket_html,
        "tarih_kisa": f"{tarih.day} {AYLAR_KISA[tarih.month - 1]}",
        "ki_etiket": e(KI_ETIKET),
        "kart_baslik": e(h["baslik"] if h["baslik"][-1:] in ".!?…" else h["baslik"] + "."),
        "kart_ozet": e(kisalt(ic.get("ozet") or "", 170)),
    }
    with open(os.path.join(KOK, f"sablon_{SABLON}.html"), encoding="utf-8") as f:
        sayfa = string.Template(f.read()).safe_substitute(degerler)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        sayfa_obj = tarayici.new_page(viewport={"width": 1080, "height": 1350})
        sayfa_obj.set_content(sayfa, wait_until="networkidle", timeout=60000)
        sayfa_obj.evaluate("document.fonts.ready")
        # Her şablon kendi "sigdir" fonksiyonuyla uzun metinleri küçültür, taşma olmaz
        sayfa_obj.evaluate("() => { if (window.sigdir) window.sigdir(); }")
        png = sayfa_obj.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
        tarayici.close()
    Image.open(BytesIO(png)).convert("RGB").save(cikti_yolu, "JPEG", quality=92)
    return cikti_yolu


# ---------------------------------------------------------------- Meta Graph API

def graph(yol):
    return f"https://graph.facebook.com/{GRAPH_VERSION}/{yol}"


def kontrol(r):
    if r.status_code >= 400:
        raise RuntimeError(f"Graph API hatası {r.status_code}: {r.text}")
    return r.json()


def facebook_paylas(gorsel, metin):
    with open(gorsel, "rb") as f:
        sonuc = kontrol(HTTP.post(graph(f"{PAGE_ID}/photos"),
                                  data={"message": metin, "access_token": PAGE_TOKEN},
                                  files={"source": ("gorsel.jpg", f, "image/jpeg")}, timeout=120))
    foto_id = sonuc["id"]
    # Instagram için herkese açık bir görsel adresi gerekiyor: Facebook'a yüklenen fotoğrafın adresi kullanılır
    bilgi = kontrol(HTTP.get(graph(foto_id), params={"fields": "images", "access_token": PAGE_TOKEN}, timeout=30))
    en_buyuk = max(bilgi["images"], key=lambda i: i["width"])
    return sonuc.get("post_id", foto_id), en_buyuk["source"]


def instagram_paylas(gorsel_url, metin):
    kap = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media"),
                            data={"image_url": gorsel_url, "caption": metin, "access_token": PAGE_TOKEN},
                            timeout=60))
    kap_id = kap["id"]
    for _ in range(30):
        durum = kontrol(HTTP.get(graph(kap_id), params={"fields": "status_code", "access_token": PAGE_TOKEN},
                                 timeout=30)).get("status_code")
        if durum == "FINISHED":
            break
        if durum == "ERROR":
            raise RuntimeError("Instagram görseli işleyemedi")
        time.sleep(4)
    yayin = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media_publish"),
                              data={"creation_id": kap_id, "access_token": PAGE_TOKEN}, timeout=60))
    return yayin["id"]


# ---------------------------------------------------------------- Ana akış

def main():
    os.makedirs(CIKTI, exist_ok=True)
    paylasilanlar = durum_oku()
    haber = haber_sec(haberleri_getir(), paylasilanlar)
    if not haber:
        log("Paylaşılacak yeni haber yok.")
        return 0
    log("Seçilen haber:", haber["baslik"])

    ic = icerik_hazirla(haber)
    damga = dt.datetime.now().strftime("%Y%m%d-%H%M")
    gorsel = gorsel_uret(haber, ic, os.path.join(CIKTI, f"{damga}.jpg"))
    fb_metin = paylasim_metni(haber, ic, "facebook")
    ig_metin = paylasim_metni(haber, ic, "instagram")
    with open(os.path.join(CIKTI, f"{damga}.txt"), "w", encoding="utf-8") as f:
        f.write(f"--- FACEBOOK ---\n{fb_metin}\n\n--- INSTAGRAM ---\n{ig_metin}\n")
    log("Görsel hazır:", gorsel)

    if DRY_RUN:
        log("DENEME MODU (DRY_RUN=1): paylaşım yapılmadı.")
        return 0
    if not (PAGE_ID and PAGE_TOKEN):
        log("HATA: META_PAGE_ID / META_PAGE_TOKEN tanımlı değil.")
        return 1

    kayit = {"link": haber["link"], "baslik": haber["baslik"],
             "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    fb_id, gorsel_url = facebook_paylas(gorsel, fb_metin)
    kayit["facebook"] = fb_id
    log("Facebook'ta paylaşıldı:", fb_id)
    # Facebook başarılıysa haberi hemen kaydet; Instagram hata verse bile Facebook'ta tekrar paylaşılmaz
    paylasilanlar.append(kayit)
    durum_yaz(paylasilanlar)

    if IG_USER_ID:
        try:
            kayit["instagram"] = instagram_paylas(gorsel_url, ig_metin)
            log("Instagram'da paylaşıldı:", kayit["instagram"])
        except Exception as e:
            kayit["instagram_hata"] = str(e)[:300]
            log("Instagram hatası:", e)
            gh_hata("Instagram paylaşım hatası", e)
        durum_yaz(paylasilanlar)
    return 0


def gh_hata(baslik, mesaj):
    """Hatayı GitHub Actions özetinde görünür bir not olarak yazar (anahtarlar gizlenir)."""
    mesaj = str(mesaj)
    if PAGE_TOKEN:
        mesaj = mesaj.replace(PAGE_TOKEN, "***")
    mesaj = mesaj.replace("%", "%25").replace("\r", "").replace("\n", "%0A")[:1500]
    print(f"::error title={baslik}::{mesaj}", flush=True)


def baglanti_kontrol():
    """Paylaşımdan önce: anahtar, sayfa ve Instagram hesabı erişilebilir mi?"""
    if not (PAGE_ID and PAGE_TOKEN):
        ham = {ad: len(os.getenv(ad) or "") for ad in ("META_PAGE_ID", "META_PAGE_TOKEN", "IG_USER_ID")}
        raise RuntimeError(f"Eksik değer. Okunan uzunluklar (ham): {ham}; temizlendikten sonra: "
                           f"META_PAGE_ID={len(PAGE_ID)}, META_PAGE_TOKEN={len(PAGE_TOKEN)}")
    bilgi = (f"Anahtar uzunluğu {len(PAGE_TOKEN)} karakter, başlangıcı {PAGE_TOKEN[:3]}, "
             f"temizlenen fazla karakter {TOKEN_TEMIZLENEN}")
    log(bilgi)
    try:
        sayfa = kontrol(HTTP.get(graph(PAGE_ID), params={"fields": "name", "access_token": PAGE_TOKEN},
                                 timeout=30))
    except Exception as e:
        raise RuntimeError(f"{e} | {bilgi}")
    log("Facebook sayfası erişilebilir:", sayfa.get("name"))
    if IG_USER_ID:
        ig = kontrol(HTTP.get(graph(IG_USER_ID), params={"fields": "username", "access_token": PAGE_TOKEN},
                              timeout=30))
        log("Instagram hesabı erişilebilir:", ig.get("username"))
    else:
        log("UYARI: IG_USER_ID boş, Instagram'a paylaşım yapılmayacak.")


def yeni_haber_var_mi():
    """Hafif kontrol: paylaşılacak yeni haber var mı? (Ağır kurulumdan önce çalışır.)"""
    haber = haber_sec(haberleri_getir(), durum_oku())
    log("Yeni haber:", haber["baslik"] if haber else "yok")
    cikti = os.getenv("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write(f"yeni={'true' if haber else 'false'}\n")


if __name__ == "__main__":
    if "--kontrol" in sys.argv:
        try:
            yeni_haber_var_mi()
            sys.exit(0)
        except Exception as hata:
            gh_hata("Havadis kontrol hatası", f"{type(hata).__name__}: {hata}")
            sys.exit(1)
    if os.getenv("CHECK_ONLY") == "1":
        # Sadece anahtar/sayfa/Instagram erişimini kontrol et, paylaşım yapma
        try:
            baglanti_kontrol()
            log("Bağlantı kontrolü başarılı.")
            sys.exit(0)
        except Exception as hata:
            gh_hata("Bağlantı kontrolü başarısız", f"{type(hata).__name__}: {hata}")
            sys.exit(1)
    try:
        if not DRY_RUN:
            baglanti_kontrol()
        sys.exit(main())
    except Exception as hata:
        gh_hata("Havadis paylaşım hatası", f"{type(hata).__name__}: {hata}")
        sys.exit(1)
