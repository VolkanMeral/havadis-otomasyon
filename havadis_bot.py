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
def kat_norm(metin):
    """Kategori adını karşılaştırma için sadeleştirir (İ/I/ı farkı, büyük-küçük harf)."""
    return metin.replace("İ", "i").replace("I", "i").replace("ı", "i").casefold().strip()


def kategori_eslesir(kategori, kume):
    """'Teknoloji/Bilim' gibi alt başlıklı kategoriler ilk kelimesiyle de eşleşir (örn. 'Teknoloji')."""
    n = kat_norm(kategori)
    return n in kume or n.split("/")[0].strip() in kume


ATLANACAK_KATEGORILER = {
    kat_norm(k) for k in os.getenv("SKIP_CATEGORIES", "TAZİYE").split(",") if k.strip()
}
# Sadece bu kategorilerdeki haberler paylaşılır (boş bırakılırsa tüm kategoriler)
PAYLASILACAK_KATEGORILER = {
    kat_norm(k)
    for k in os.getenv("INCLUDE_CATEGORIES", "Avusturya,Vorarlberg,Almanya,İsviçre,Sağlık,Dünya,Teknoloji,Havadis Özel,Avrupa").split(",") if k.strip()
}
# Video ayarları
# Akışta video (Reels) paylaşılacak saatler (Viyana saati). Video çalışmaları her saat 15 geçe başlar,
# sadece bu saatlerde gerçekten paylaşım yapar; böylece saat başı/buçuktaki görsellerle çakışmaz.
VIDEO_SAATLERI = {int(x) for x in os.getenv("VIDEO_HOURS", "7,8,10,11,13,14,16,17,19,20").split(",") if x.strip().isdigit()}
# TikTok'a video gönderilecek saatler (Viyana). Taslak modunda TikTok en fazla 5 bekleyen taslağa izin verir.
TIKTOK_SAATLERI = {int(x) for x in os.getenv("TIKTOK_HOURS", "8,11,14,17,20").split(",") if x.strip().isdigit()}
# Bu kategorilerdeki haberler ayrıca Instagram Story'ye video olarak gider
STORY_KATEGORILERI = {
    kat_norm(k) for k in os.getenv("STORY_CATEGORIES", "Avusturya,Vorarlberg").split(",") if k.strip()
}
# Çalışma türü GitHub zamanlamasından belirlenir
ZAMANLAMALAR = {
    "0 6-20 * * *": "saat",          # saat başı: görsel
    "30 6-20 * * *": "bucuk",        # buçuk: Vorarlberg görsel
    "15 5-20 * * *": "video",        # 15 geçe: video (sadece VIDEO_HOURS saatlerinde)
    "45 17,18 * * 0": "haftalik",    # pazar 19:45 Viyana: "Vorarlberg'de bu hafta" karuseli
    "45 17,18 * * 3": "rehber",      # çarşamba 19:45 Viyana: "Bilmeniz gerekenler" karuseli
    "5 9,10 * * 0": "ozet",          # pazar 11:05 Viyana: "Avusturya'da bu hafta" özet videosu
}
CALISMA_TURU = os.getenv("RUN_SLOT") or ZAMANLAMALAR.get(os.getenv("SCHEDULE", ""), "saat")
if os.getenv("JOB", "normal") in ("haftalik", "rehber", "ozet"):   # elle çalıştırma
    CALISMA_TURU = os.getenv("JOB")
ELLE = os.getenv("GITHUB_EVENT_NAME") == "workflow_dispatch"
if CALISMA_TURU == "bucuk":
    PAYLASILACAK_KATEGORILER = {kat_norm(k) for k in
                                os.getenv("HALF_HOUR_CATEGORIES", "Vorarlberg").split(",") if k.strip()}
VIDEO_ZORLA = os.getenv("FORCE_VIDEO", "0") == "1"  # elle deneme için

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
# Threads: ayrı bir kullanıcı anahtarı (threads_basic + threads_content_publish). Boşsa Threads atlanır.
THREADS_TOKEN, _ = _temiz(os.getenv("THREADS_TOKEN"), r"[^A-Za-z0-9]")


def _sayfa_anahtari(anahtar):
    """META_PAGE_TOKEN bir sistem kullanıcısı/kullanıcı anahtarıysa, sayfanın kendi (süresiz) anahtarını alır.
    Zaten sayfa anahtarıysa veya istek başarısız olursa anahtarı olduğu gibi döndürür."""
    if not (anahtar and PAGE_ID):
        return anahtar
    try:
        r = requests.get(f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}",
                         params={"fields": "access_token", "access_token": anahtar}, timeout=15)
        yeni = r.json().get("access_token") if r.status_code == 200 else None
        return yeni or anahtar
    except Exception:
        return anahtar


ORIJINAL_TOKEN = PAGE_TOKEN
PAGE_TOKEN = _sayfa_anahtari(PAGE_TOKEN)

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

class RssEngeli(RuntimeError):
    """Site RSS yerine bir koruma/ara sayfa döndürdü (geçici)."""


def haberleri_getir():
    """RSS'i okur. XML'in tamamı bozuk olsa bile her haberi ayrı ayrı ayıklar
    (sitedeki tek bir hatalı haber diğerlerini engellemesin diye)."""
    # Site bazen RSS yerine bir koruma/ara sayfa döndürüyor: farklı tarayıcı kimliğiyle birkaç kez yeniden dene
    tarayici_basliklari = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/130.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5",
        "Accept-Language": "tr-TR,tr;q=0.9,de;q=0.8"}
    metin = ""
    for deneme in range(4):
        try:
            r = HTTP.get(RSS_URL, timeout=30, headers=tarayici_basliklari if deneme % 2 else None)
            r.raise_for_status()
            metin = r.content.decode("utf-8", errors="replace")
            if "<item" not in metin:
                raise RssEngeli(f"RSS yerine farklı bir sayfa geldi (ilk 200 karakter): {metin[:200]!r}")
            break
        except Exception as hata:
            if deneme == 3:
                if isinstance(hata, RssEngeli):
                    # Teşhis için sayfanın betik kısmını not düş
                    print(f"::warning title=RSS koruma sayfası (teşhis)::{metin[:1500]!r}", flush=True)
                raise
            log(f"RSS alınamadı ({hata.__class__.__name__}), {20 * (deneme + 1)} sn sonra yeniden denenecek…")
            time.sleep(20 * (deneme + 1))
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
    try:
        arsiv_guncelle(haberler)
    except Exception as e:
        log("Arşiv güncellenemedi:", e)
    return haberler


ARSIV = os.path.join(KOK, "arsiv.json")


def arsiv_oku():
    return json.load(open(ARSIV, encoding="utf-8")) if os.path.exists(ARSIV) else []


def arsiv_guncelle(haberler):
    """RSS'te görülen haberleri 15 gün saklar (haftalık özet için)."""
    arsiv = {h["link"]: h for h in arsiv_oku()}
    for h in haberler:
        if h["link"] and h["tarih"]:
            arsiv[h["link"]] = {k: h[k] for k in ("baslik", "link", "ozet", "kategori", "resim")} | \
                               {"tarih": h["tarih"].isoformat()}
    sinir = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=15)
    kalan = [h for h in arsiv.values() if dt.datetime.fromisoformat(h["tarih"]) > sinir]
    kalan.sort(key=lambda h: h["tarih"])
    with open(ARSIV, "w", encoding="utf-8") as f:
        json.dump(kalan, f, ensure_ascii=False, indent=1)


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
        if kategori_eslesir(h["kategori"], ATLANACAK_KATEGORILER):
            continue
        if PAYLASILACAK_KATEGORILER and not kategori_eslesir(h["kategori"], PAYLASILACAK_KATEGORILER):
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


def merak_girisi(metin, n=110):
    """Özetin ilk cümlesinden kısa bir giriş: haberin tamamını vermez, devamı sitede."""
    ilk = re.split(r"(?<=[.!?])\s+", metin.strip())[0] if metin else ""
    if len(ilk) > n:
        ilk = ilk[:n].rsplit(" ", 1)[0].rstrip(",;:")
    return ilk.rstrip(".!?") + "…" if ilk else ""


def paylasim_metni(h, ic, platform):
    kat = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", h["kategori"])
    etiketler = " ".join(dict.fromkeys((ic["hashtagler"] + " " + SABIT_HASHTAGLER + (f" #{kat}" if kat else "")).split()))
    ki = f"\n\n🤖 {KI_ETIKET}" if KI_ETIKET else ""
    if platform == "facebook":
        # Facebook'ta metin alanında sadece haber linki: haberi okumak isteyen linke tıklar.
        # (Başlık ve "KI-unterstützt" notu görselin üzerinde zaten yazıyor.)
        return h["link"]
    devam = f"👉 Haberin tamamı: {h['link']}"
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


def threads_metni(h, ic):
    """Threads gönderisi (en fazla 500 karakter): link tıklanabilir ve önizleme kartı olarak görünür."""
    kat = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", h["kategori"])
    ki = f"\n\n🤖 {KI_ETIKET}" if KI_ETIKET else ""
    son = f"\n\n👉 {h['link']}{ki}" + (f"\n\n#{kat}" if kat else "")
    bas = f"{h['baslik']}\n\n"
    yer = min(280, 470 - len(bas) - len(son))  # emojiler bayt olarak sayıldığı için pay bırakılır
    ozet = kisalt(ic.get("metin") or h.get("ozet") or "", yer) if yer > 40 else ""
    return (bas + ozet + son).strip()


def tam_ekran_hazirla(foto, w=1080, h=1350, foto_ust=0, dikey_odak=0.3):
    """Fotoğrafı tam ekran tasarıma hazırlar.
    Yatay fotoğraflar KESİLMEZ: fotoğrafın tamamı üstte tam genişlikte durur, arka plan aynı fotoğrafın
    bulanık ve karartılmış haliyle dolar. Dikey fotoğraflar eskisi gibi tüm alanı kaplar."""
    from PIL import ImageEnhance, ImageFilter
    oran_foto = foto.width / foto.height

    def kapla(img, gw, gh):
        o = max(gw / img.width, gh / img.height)
        y_ = img.resize((round(img.width * o), round(img.height * o)), Image.LANCZOS)
        x0, y0 = (y_.width - gw) // 2, int((y_.height - gh) * dikey_odak)
        return y_.crop((x0, y0, x0 + gw, y0 + gh)), o

    if oran_foto < 1.1:  # dikey/kare fotoğraf: tüm alanı kapla
        yeni, o = kapla(foto, w, h)
        return yeni.filter(ImageFilter.UnsharpMask(radius=2, percent=70, threshold=2)) if o > 1.2 else yeni

    # Arka plan: bulanık, karartılmış
    arka, _ = kapla(foto, w, h)
    arka = arka.resize((w // 8, h // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)).resize((w, h), Image.BILINEAR)
    arka = ImageEnhance.Brightness(arka).enhance(0.45)
    # Ön plan: fotoğrafın tamamı, tam genişlikte
    fh = round(w / oran_foto)
    on = foto.resize((w, fh), Image.LANCZOS)
    if w / foto.width > 1.2:
        on = on.filter(ImageFilter.UnsharpMask(radius=2, percent=80, threshold=2))
    # Alt kenarı arka plana yumuşakça karışsın
    maske = Image.new("L", (w, fh), 255)
    gecis = min(160, fh // 4)
    for i in range(gecis):
        maske.paste(int(255 * (1 - i / gecis) ** 1.5), (0, fh - gecis + i, w, fh - gecis + i + 1))
    arka.paste(on, (0, foto_ust), maske)
    return arka


def sayfa_hazirla(h, ic, foto_bayt=None, boyut=(1080, 1350), foto_ust=0):
    """Seçili şablonu haber bilgileriyle doldurup HTML olarak döndürür (görsel ve video aynı tasarımı kullanır)."""
    if foto_bayt is None:
        r = HTTP.get(h["resim"], timeout=60)
        r.raise_for_status()
        foto_bayt = r.content
    foto = Image.open(BytesIO(foto_bayt)).convert("RGB")
    if SABLON == "manset":
        foto = tam_ekran_hazirla(foto, boyut[0], boyut[1], foto_ust)
    tampon = BytesIO()
    foto.save(tampon, "JPEG", quality=92)

    tarih = h["tarih"] or dt.datetime.now()
    e = html.escape
    tam_baslik = f"{ic['baslik_beyaz']} {ic['baslik_vurgu']}".strip()
    baslik_html = (f'<span class="beyaz">{e(ic["baslik_beyaz"])}</span><br>' if ic["baslik_beyaz"] else "") + \
        f'<span class="vurgu">{e(ic["baslik_vurgu"])}</span>'
    degerler = {
        "foto": veri_uri(tampon.getvalue(), "image/jpeg"),
        "logo": veri_uri(os.path.join(KOK, "assets", "logo-beyaz.png"), "image/png"),
        "tarih": f"{tarih.day} {AYLAR[tarih.month - 1]} {tarih.year}",
        "kategori": e(h["kategori"]),
        "ust_baslik_html": f'<div class="ust-baslik">{e(ic["ust_baslik"])}</div>' if ic.get("ust_baslik") else "",
        "baslik_html": baslik_html,
        "baslik_px": f"{baslik_boyutu(tam_baslik)}px",
        "ozet_html": f'<p class="ozet">{e(ic["ozet"])}</p>' if ic.get("ozet") else "",
        "etiket_html": "",
        "tarih_kisa": f"{tarih.day} {AYLAR_KISA[tarih.month - 1]}",
        "ki_etiket": e(KI_ETIKET),
        "kart_baslik": e(h["baslik"] if h["baslik"][-1:] in ".!?…" else h["baslik"] + "."),
        "kart_ozet": e(kisalt(ic.get("ozet") or "", 170)),
    }
    with open(os.path.join(KOK, f"sablon_{SABLON}.html"), encoding="utf-8") as f:
        return string.Template(f.read()).safe_substitute(degerler)


def gorsel_uret(h, ic, cikti_yolu, foto_bayt=None):
    sayfa = sayfa_hazirla(h, ic, foto_bayt)
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


THREADS_API = "https://graph.threads.net/v1.0"


def threads_paylas(metin, link):
    """Threads'e metin + link önizlemesi paylaşır (iki adım: kap oluştur, yayınla)."""
    kap = kontrol(HTTP.post(f"{THREADS_API}/me/threads", data={
        "media_type": "TEXT", "text": metin, "link_attachment": link, "access_token": THREADS_TOKEN}, timeout=60))["id"]
    son_hata = None
    for bekle in (3, 10, 20, 30):  # Meta, yayınlamadan önce kısa bir bekleme öneriyor
        time.sleep(bekle)
        r = HTTP.post(f"{THREADS_API}/me/threads_publish",
                      data={"creation_id": kap, "access_token": THREADS_TOKEN}, timeout=60)
        if r.status_code < 400:
            return r.json()["id"]
        son_hata = r.text
    raise RuntimeError(f"Threads yayınlanamadı: {son_hata}")


def ig_bekle(kap_id, deneme=30, aralik=4):
    """Instagram medya kabının işlenmesini bekler."""
    for _ in range(deneme):
        durum = kontrol(HTTP.get(graph(kap_id), params={"fields": "status_code,status", "access_token": PAGE_TOKEN},
                                 timeout=30))
        if durum.get("status_code") == "FINISHED":
            return
        if durum.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram medyayı işleyemedi: {durum.get('status')}")
        time.sleep(aralik)
    raise RuntimeError("Instagram medya işleme zaman aşımı")


def _yukle(adres, dosya):
    """Meta'nın 'resumable upload' adresine dosyayı tek seferde yükler (herkese açık link gerekmez)."""
    with open(dosya, "rb") as f:
        veri = f.read()
    return kontrol(HTTP.post(adres, data=veri, timeout=300, headers={
        "Authorization": f"OAuth {PAGE_TOKEN}", "offset": "0", "file_size": str(len(veri))}))


def instagram_video(video, tur, metin=None):
    """tur: 'REELS' (akış) veya 'STORIES' (hikâye)."""
    veri = {"media_type": tur, "upload_type": "resumable", "access_token": PAGE_TOKEN}
    if metin:
        veri["caption"] = metin
    if tur == "REELS":
        veri["share_to_feed"] = "true"
        veri["thumb_offset"] = "4500"  # kapak: 4,5. saniye (tüm yazılar görünür), ilk kare karanlık
    kap = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media"), data=veri, timeout=60))
    adres = kap.get("uri") or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_VERSION}/{kap['id']}"
    _yukle(adres, video)
    ig_bekle(kap["id"], deneme=60, aralik=5)
    yayin = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media_publish"),
                              data={"creation_id": kap["id"], "access_token": PAGE_TOKEN}, timeout=60))
    return yayin["id"]


def facebook_reel(video, metin, kapak=None):
    bas = kontrol(HTTP.post(graph(f"{PAGE_ID}/video_reels"),
                            data={"upload_phase": "start", "access_token": PAGE_TOKEN}, timeout=60))
    _yukle(bas["upload_url"], video)
    kontrol(HTTP.post(graph(f"{PAGE_ID}/video_reels"), timeout=60, data={
        "upload_phase": "finish", "video_id": bas["video_id"], "video_state": "PUBLISHED",
        "description": metin, "access_token": PAGE_TOKEN}))
    if kapak:
        try:
            with open(kapak, "rb") as f:
                kontrol(HTTP.post(graph(f"{bas['video_id']}/thumbnails"), timeout=60,
                                  data={"is_preferred": "true", "access_token": PAGE_TOKEN},
                                  files={"source": ("kapak.jpg", f, "image/jpeg")}))
        except Exception as e:
            log("Facebook Reels kapağı ayarlanamadı (video yine de yayında):", e)
    return bas["video_id"]


def facebook_story(video):
    """Facebook sayfasında video Story paylaşır (Page Stories API)."""
    bas = kontrol(HTTP.post(graph(f"{PAGE_ID}/video_stories"),
                            data={"upload_phase": "start", "access_token": PAGE_TOKEN}, timeout=60))
    _yukle(bas["upload_url"], video)
    son = kontrol(HTTP.post(graph(f"{PAGE_ID}/video_stories"), timeout=60, data={
        "upload_phase": "finish", "video_id": bas["video_id"], "access_token": PAGE_TOKEN}))
    return son.get("post_id") or bas["video_id"]


def instagram_paylas(gorsel_url, metin):
    kap = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media"),
                            data={"image_url": gorsel_url, "caption": metin, "access_token": PAGE_TOKEN},
                            timeout=60))
    ig_bekle(kap["id"])
    yayin = kontrol(HTTP.post(graph(f"{IG_USER_ID}/media_publish"),
                              data={"creation_id": kap["id"], "access_token": PAGE_TOKEN}, timeout=60))
    return yayin["id"]


# ---------------------------------------------------------------- Ana akış

def viyana_saati():
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("Europe/Vienna")).hour


def video_saati_mi():
    return CALISMA_TURU != "video" or VIDEO_ZORLA or viyana_saati() in VIDEO_SAATLERI


def karusel_saati_mi():
    return ELLE or viyana_saati() == 19


def main():
    os.makedirs(CIKTI, exist_ok=True)
    if CALISMA_TURU == "ozet":
        import haftalik_ozet
        if not haftalik_ozet.ozet_saati_mi():
            log("Haftalık özet videosu saati değil.")
            return 0
        return haftalik_ozet.calistir()
    if CALISMA_TURU in ("haftalik", "rehber"):
        if not karusel_saati_mi():
            log("Karusel saati değil.")
            return 0
        import karusel
        return karusel.haftalik_calistir() if CALISMA_TURU == "haftalik" else karusel.rehber_calistir()
    if not video_saati_mi():
        log("Bu saat video paylaşım saati değil.")
        return 0
    paylasilanlar = durum_oku()
    haber = haber_sec(haberleri_getir(), paylasilanlar)
    if not haber:
        log("Paylaşılacak yeni haber yok.")
        return 0
    log("Seçilen haber:", haber["baslik"], "|", haber["kategori"])

    ic = icerik_hazirla(haber)
    damga = dt.datetime.now().strftime("%Y%m%d-%H%M")
    r = HTTP.get(haber["resim"], timeout=60)
    r.raise_for_status()
    foto = r.content

    video_akis = SABLON == "manset" and (VIDEO_ZORLA or CALISMA_TURU == "video")
    story = SABLON == "manset" and \
        kategori_eslesir(haber["kategori"], STORY_KATEGORILERI)
    log(f"Akışta video: {'evet' if video_akis else 'hayır'} | Story: {'evet' if story else 'hayır'}")

    fb_metin = paylasim_metni(haber, ic, "facebook")
    ig_metin = paylasim_metni(haber, ic, "instagram")
    th_metin = threads_metni(haber, ic)
    with open(os.path.join(CIKTI, f"{damga}.txt"), "w", encoding="utf-8") as f:
        f.write(f"--- FACEBOOK ---\n{fb_metin}\n\n--- INSTAGRAM ---\n{ig_metin}\n\n--- THREADS ---\n{th_metin}\n")

    gorsel = None if video_akis else gorsel_uret(haber, ic, os.path.join(CIKTI, f"{damga}.jpg"), foto)
    video = None
    if video_akis or story:
        import video_uret
        video = video_uret.video_uret(haber, ic, os.path.join(CIKTI, f"{damga}.mp4"), foto)
        kapak = video_uret.kapak_uret(video, os.path.join(CIKTI, f"{damga}-kapak.jpg"))
        log("Video hazır:", video)
    if gorsel:
        log("Görsel hazır:", gorsel)

    if DRY_RUN:
        log("DENEME MODU (DRY_RUN=1): paylaşım yapılmadı.")
        return 0
    if not (PAGE_ID and PAGE_TOKEN):
        log("HATA: META_PAGE_ID / META_PAGE_TOKEN tanımlı değil.")
        return 1

    kayit = {"link": haber["link"], "baslik": haber["baslik"], "tur": "video" if video_akis else "gorsel",
             "zaman": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}

    def kaydet():
        if kayit not in paylasilanlar:
            paylasilanlar.append(kayit)
        durum_yaz(paylasilanlar)

    def dene(ad, is_):
        try:
            kayit[ad] = is_()
            log(f"{ad} paylaşıldı:", kayit[ad])
        except Exception as e:
            kayit[f"{ad}_hata"] = str(e)[:300]
            log(f"{ad} hatası:", e)
            gh_hata(f"{ad} hatası", e)
        kaydet()

    if video_akis:
        dene("facebook_reel", lambda: facebook_reel(video, fb_metin, kapak))
        if IG_USER_ID:
            dene("instagram_reel", lambda: instagram_video(video, "REELS", ig_metin))
    else:
        fb_id, gorsel_url = facebook_paylas(gorsel, fb_metin)
        kayit["facebook"] = fb_id
        log("Facebook'ta paylaşıldı:", fb_id)
        # Facebook başarılıysa haberi hemen kaydet; sonraki adımlar hata verse bile tekrar paylaşılmaz
        kaydet()
        if IG_USER_ID:
            dene("instagram", lambda: instagram_paylas(gorsel_url, ig_metin))

    if story:
        if IG_USER_ID:
            dene("instagram_story", lambda: instagram_video(video, "STORIES"))
        dene("facebook_story", lambda: facebook_story(video))

    if THREADS_TOKEN:
        dene("threads", lambda: threads_paylas(th_metin, haber["link"]))

    if video_akis and (VIDEO_ZORLA or viyana_saati() in TIKTOK_SAATLERI):
        import tiktok
        if tiktok.hazir_mi():
            tt_metin = f"{haber['baslik']}\n\n{kisalt(ic['metin'], 300)}\n\nHaberin tamamı havadis.at'de" + \
                (f"\n\n🤖 {KI_ETIKET}" if KI_ETIKET else "") + "\n\n#havadis #avusturya #haber"
            dene("tiktok", lambda: tiktok.paylas(video, tt_metin))
            try:
                if tiktok.kalan_gun() < 30:
                    gh_hata("TikTok bağlantısı yakında bitiyor",
                            f"{tiktok.kalan_gun():.0f} gün kaldı: GitHub'da tiktok_kod ile yeniden bağlayın.")
            except Exception:
                pass

    if video_akis:
        import youtube
        if youtube.hazir_mi():
            yt_aciklama = (f"{haber['baslik']}\n\n{kisalt(ic['metin'], 600)}\n\n"
                           f"👉 Haberin tamamı: {haber['link']}"
                           + (f"\n\n🤖 {KI_ETIKET}" if KI_ETIKET else "") + "\n\n#havadis #Avusturya #haber #Shorts")
            kat = re.sub(r"[^\wçğıöşüÇĞİÖŞÜ]", "", haber["kategori"])
            dene("youtube", lambda: youtube.yukle(video, haber["baslik"], yt_aciklama,
                                                  ["havadis", "Avusturya", "haber", kat]))

    # Hiçbir platformda paylaşılamadıysa görev hata versin
    if not any(k in kayit for k in ("facebook", "facebook_reel", "instagram", "instagram_reel")):
        raise RuntimeError("Haber hiçbir platformda paylaşılamadı (ayrıntılar yukarıdaki notlarda).")
    return 0


def gh_hata(baslik, mesaj):
    """Hatayı GitHub Actions özetinde görünür bir not olarak yazar (anahtarlar gizlenir)."""
    mesaj = str(mesaj)
    for gizli in (PAGE_TOKEN, ORIJINAL_TOKEN, THREADS_TOKEN):
        if gizli:
            mesaj = mesaj.replace(gizli, "***")
    mesaj = mesaj.replace("%", "%25").replace("\r", "").replace("\n", "%0A")[:1500]
    print(f"::error title={baslik}::{mesaj}", flush=True)


def baglanti_kontrol():
    """Paylaşımdan önce: anahtar, sayfa ve Instagram hesabı erişilebilir mi?"""
    if not (PAGE_ID and PAGE_TOKEN):
        ham = {ad: len(os.getenv(ad) or "") for ad in ("META_PAGE_ID", "META_PAGE_TOKEN", "IG_USER_ID")}
        raise RuntimeError(f"Eksik değer. Okunan uzunluklar (ham): {ham}; temizlendikten sonra: "
                           f"META_PAGE_ID={len(PAGE_ID)}, META_PAGE_TOKEN={len(PAGE_TOKEN)}")
    tur = "sistem/kullanıcı anahtarından alınan sayfa anahtarı" if PAGE_TOKEN != ORIJINAL_TOKEN else "doğrudan sayfa anahtarı"
    bilgi = (f"Anahtar türü: {tur}; uzunluk {len(ORIJINAL_TOKEN)} karakter, başlangıcı {ORIJINAL_TOKEN[:3]}, "
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
    if THREADS_TOKEN:
        th = kontrol(HTTP.get(f"{THREADS_API}/me", params={"fields": "username", "access_token": THREADS_TOKEN},
                              timeout=30))
        log("Threads hesabı erişilebilir:", th.get("username"))
    else:
        log("Bilgi: THREADS_TOKEN boş, Threads'e paylaşım yapılmayacak.")


def yeni_haber_var_mi():
    """Hafif kontrol: paylaşılacak yeni haber var mı? (Ağır kurulumdan önce çalışır.)"""
    if CALISMA_TURU in ("haftalik", "rehber"):
        haberleri_getir()  # arşivi güncel tut
        haber = {"baslik": f"{CALISMA_TURU} karuseli"} if karusel_saati_mi() else None
    elif CALISMA_TURU == "ozet":
        haberleri_getir()
        haber = {"baslik": "haftalık özet videosu"} if (ELLE or viyana_saati() == 11) else None
    else:
        haber = haber_sec(haberleri_getir(), durum_oku()) if video_saati_mi() else None
    log("Yeni haber:", haber["baslik"] if haber else "yok (ya da video saati değil)")
    cikti = os.getenv("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write(f"yeni={'true' if haber else 'false'}\n")


if __name__ == "__main__":
    if "--kontrol" in sys.argv:
        try:
            yeni_haber_var_mi()
            sys.exit(0)
        except (RssEngeli, requests.RequestException) as hata:
            print(f"::warning title=RSS şu an alınamadı, bu çalışma atlandı::{type(hata).__name__}: {str(hata)[:300]}")
            cikti = os.getenv("GITHUB_OUTPUT")
            if cikti:
                with open(cikti, "a", encoding="utf-8") as f:
                    f.write("yeni=false\n")
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
    except (RssEngeli, requests.RequestException) as hata:
        print(f"::warning title=RSS şu an alınamadı, bu çalışma atlandı::{type(hata).__name__}: {str(hata)[:300]}")
        sys.exit(0)
    except Exception as hata:
        gh_hata("Havadis paylaşım hatası", f"{type(hata).__name__}: {hata}")
        sys.exit(1)
