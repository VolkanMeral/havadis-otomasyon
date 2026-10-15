#!/usr/bin/env python3
"""Sesli haftalık rapor videosu: "Vorarlberg'de bu hafta" – Türkçe yapay ses, altta çerçeveli altyazı.
Bu betik sadece video DOSYASI üretir, paylaşım yapmaz.
Kullanım: python haftalik_video.py <piper_ses_modeli.onnx> <çıktı.mp4> [hedef_saniye]"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import wave
from io import BytesIO

from PIL import Image

import havadis_bot as bot
import karusel

MODEL, CIKTI = sys.argv[1], sys.argv[2]
HEDEF = float(sys.argv[3]) if len(sys.argv) > 3 else 180.0
FPS = 24
W, H = 1080, 1920
GECICI = os.path.join(bot.KOK, "cikti", "haftalik_ses")
os.makedirs(GECICI, exist_ok=True)
E = html.escape


# ---------------------------------------------------------------- Seslendirme metni

BIRLER = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
ONLAR = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]


def yuzluk(n):
    y, o, b = n // 100, (n // 10) % 10, n % 10
    return " ".join(x for x in [("" if y == 1 else BIRLER[y]) + (" yüz" if y else ""), ONLAR[o], BIRLER[b]] if x).strip()


def turkce_sayi(n):
    """Tam sayıyı Türkçe yazıya çevirir (örn. 17500 → on yedi bin beş yüz)."""
    if n == 0:
        return "sıfır"
    parcalar = []
    for deger, ad in ((10 ** 9, "milyar"), (10 ** 6, "milyon"), (1000, "bin")):
        k, n = divmod(n, deger)
        if k:
            parcalar.append("bin" if (ad == "bin" and k == 1) else f"{turkce_sayi(k)} {ad}")
    if n:
        parcalar.append(yuzluk(n))
    return " ".join(parcalar)


def sayi_yaziya(m):
    tam, ondalik = m.group(1).replace(".", ""), m.group(2)
    s = turkce_sayi(int(tam))
    if ondalik:
        s += " virgül " + turkce_sayi(int(ondalik))
    return s


def okunus(metin):
    """Ekranda yazan metni, yapay sesin doğru okuyacağı hale getirir (rakamlar yazıyla, sembollerle)."""
    t = metin.replace("’", "'").replace("“", "").replace("”", "").replace('"', "")
    t = re.sub(r"(\d)\s*[–-]\s*(\d)", r"\1 ile \2", t)               # 19–23 → 19 ile 23
    t = re.sub(r"%\s*(\d+(?:,\d+)?)", r"yüzde \1", t)                 # %35 → yüzde 35
    t = re.sub(r"(\d+(?:,\d+)?)\s*%", r"yüzde \1", t)
    t = re.sub(r"\s*€", " avro", t)
    t = re.sub(r"\bEuro(?:'?(?:ya|yu|nun|luk|lık|dan|da))?\b", lambda m: "avro" + m.group(0)[4:].replace("'", ""), t)
    t = re.sub(r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?", sayi_yaziya, t)
    t = t.replace(":", ".").replace("!", ".")
    return re.sub(r"\s+", " ", t).strip()


def cumlelere_bol(metin):
    return [c.strip() for c in re.split(r"(?<=[.!?])\s+", metin) if c.strip()]


def seslendir(metin, yol):
    subprocess.run(["piper", "--model", MODEL, "--output_file", yol], input=metin.encode("utf-8"), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with wave.open(yol) as w:
        return w.getnframes() / w.getframerate()


# ---------------------------------------------------------------- Haberler

def haftanin_vorarlberg_haberleri(adet=12):
    haberler = bot.haberleri_getir()  # arşivi de günceller
    simdi = dt.datetime.now(dt.timezone.utc)
    secim = [h for h in haberler if h["kategori"].casefold() == "vorarlberg" and h["tarih"] and h["resim"]
             and (simdi - h["tarih"]).days < 7]
    # RSS yetmezse arşivden tamamla
    linkler = {h["link"] for h in secim}
    for a in bot.arsiv_oku():
        t = dt.datetime.fromisoformat(a["tarih"])
        if a["link"] not in linkler and a["kategori"].casefold() == "vorarlberg" and (simdi - t).days < 7:
            secim.append(dict(a, tarih=t))
    secim.sort(key=lambda h: h["tarih"], reverse=True)
    return secim[:adet]


def foto(url, w, h):
    r = bot.HTTP.get(url, timeout=60)
    r.raise_for_status()
    return karusel.foto_uri(r.content, w, h)


# ---------------------------------------------------------------- Zaman çizelgesi (ses + altyazı + bölümler)

class Zaman:
    def __init__(self):
        self.t = 0.0
        self.parcalar = []    # (dosya, başlangıç)
        self.altyazi = []     # (başlangıç, bitiş, metin)
        self.no = 0

    def bekle(self, s):
        self.t += s

    def soyle(self, ekran_metni):
        for cumle in cumlelere_bol(ekran_metni):
            yol = os.path.join(GECICI, f"c{self.no:03d}.wav")
            self.no += 1
            sure = seslendir(okunus(cumle), yol)
            self.parcalar.append((yol, self.t))
            kelimeler = cumle.split()
            parca = [" ".join(kelimeler[i:i + 9]) for i in range(0, len(kelimeler), 9)]
            toplam = sum(len(p) for p in parca)
            bas = self.t
            for p in parca:
                d = sure * len(p) / toplam
                self.altyazi.append((round(bas, 2), round(bas + d, 2), p))
                bas += d
            self.t += sure + 0.25


def sesi_birlestir(z, yol, toplam):
    with wave.open(z.parcalar[0][0]) as w:
        hz, kanal, genislik = w.getframerate(), w.getnchannels(), w.getsampwidth()
    tampon = bytearray(int(toplam * hz) * kanal * genislik)
    for dosya, bas in z.parcalar:
        with wave.open(dosya) as w:
            veri = w.readframes(w.getnframes())
        i = int(bas * hz) * kanal * genislik
        tampon[i:i + len(veri)] = veri[:max(0, len(tampon) - i)]
    with wave.open(yol, "wb") as w:
        w.setnchannels(kanal); w.setsampwidth(genislik); w.setframerate(hz)
        w.writeframes(bytes(tampon))


# ---------------------------------------------------------------- Sayfa

CSS = """
html, body { margin: 0; padding: 0; } body { width: 1080px; height: 1920px; overflow: hidden; background: #070B14; }
.v { position: relative; width: 1080px; height: 1920px; overflow: hidden; color: #fff; font-family: 'Barlow', Arial, sans-serif; background: #070B14; }
.kos { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; }
.b { position: absolute; inset: 0; opacity: 0; }
.ust { position: absolute; left: 64px; right: 64px; top: 230px; display: flex; justify-content: space-between; align-items: center; z-index: 5; }
.ust img { width: 220px; display: block; }
.ust .sag { text-align: right; }
.etiket { display: inline-block; background: #E42320; font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 26px; letter-spacing: 3px; padding: 8px 16px; }
.ki { font-size: 20px; color: rgba(255,255,255,.65); margin-top: 8px; }
.foto { position: absolute; left: 0; top: 340px; width: 1080px; height: 640px; overflow: hidden; }
.foto img { width: 100%; height: 100%; object-fit: cover; display: block; }
.foto::after { content: ""; position: absolute; inset: 0; background: linear-gradient(rgba(7,11,20,.35), rgba(7,11,20,0) 25%, rgba(7,11,20,0) 65%, #070B14); }
.bilgi { position: absolute; left: 64px; right: 64px; top: 950px; height: 370px; display: flex; flex-direction: column; gap: 16px; }
.no { display: flex; align-items: baseline; gap: 8px; }
.no b { font-size: 96px; line-height: .8; font-weight: 900; color: #E42320; }
.no span { font-size: 36px; font-weight: 800; color: rgba(255,255,255,.5); }
.gun { font-size: 28px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.75); }
.bilgi h2 { margin: 0; font-size: 76px; line-height: 1; font-weight: 900; text-transform: uppercase; }
.giris-arka, .kapanis-arka { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.karart { position: absolute; inset: 0; background: linear-gradient(rgba(7,11,20,.75), rgba(7,11,20,.9) 50%, #070B14); }
.giris { position: absolute; left: 64px; right: 64px; top: 520px; }
.giris h1 { margin: 0; font-size: 150px; line-height: .95; font-weight: 900; text-transform: uppercase; }
.bant { background: #E42320; padding: 0 14px; }
.aralik { margin-top: 28px; font-size: 40px; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,.85); }
.kapanis { position: absolute; left: 64px; right: 64px; top: 560px; display: flex; flex-direction: column; align-items: center; gap: 44px; text-align: center; }
.kapanis img { width: 560px; }
.kapanis .cta { font-size: 64px; font-weight: 900; text-transform: uppercase; line-height: 1.1; }
.kapanis .takip { font-size: 40px; font-weight: 600; color: rgba(255,255,255,.85); }
/* Altyazı: altta, çerçeve içinde (Reels düğmelerinin üstünde) */
.altyazi { position: absolute; left: 64px; right: 64px; top: 1350px; min-height: 150px; z-index: 6; display: none;
           border: 3px solid rgba(255,255,255,.85); border-radius: 22px; background: rgba(11,11,11,.78);
           padding: 24px 32px 24px 44px; box-sizing: border-box; align-items: center; }
.altyazi::before { content: ""; position: absolute; left: 0; top: 18px; bottom: 18px; width: 10px; background: #E42320; border-radius: 0 6px 6px 0; }
.altyazi span { font-size: 46px; line-height: 1.3; font-weight: 600; }
"""

JS = """
const BOLUMLER = __BOLUMLER__, ALTYAZI = __ALTYAZI__;
const q = s => document.querySelector(s);
const ilerle = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
const yum = x => 1 - Math.pow(1 - x, 3);
const bolumler = [...document.querySelectorAll('.b')];
window.sigdir = function () {
  document.querySelectorAll('.bilgi').forEach(b => { const h = b.querySelector('h2'); let px = 76;
    while (b.scrollHeight > b.clientHeight && px > 48) { px -= 4; h.style.fontSize = px + 'px'; } });
  const g = q('.giris h1'); let px = 150; while (g.scrollWidth > g.clientWidth && px > 90) { px -= 4; g.style.fontSize = px + 'px'; }
};
window.kare = function (t) {
  BOLUMLER.forEach((b, i) => {
    const el = bolumler[i];
    const gir = yum(ilerle(t, b[0], b[0] + 0.5)), cik = 1 - yum(ilerle(t, b[1] - 0.4, b[1]));
    const o = Math.min(gir, i === BOLUMLER.length - 1 ? 1 : cik);
    el.style.opacity = o; el.style.display = o > 0 ? 'block' : 'none';
    if (o > 0) {
      const img = el.querySelector('.foto img, .giris-arka');
      if (img) img.style.transform = `scale(${1 + 0.06 * ilerle(t, b[0], b[1])})`;
      const h = el.querySelector('h2'); if (h) { const d = yum(ilerle(t, b[0] + 0.3, b[0] + 0.9)); h.style.opacity = d; h.style.transform = `translateY(${40 * (1 - d)}px)`; }
    }
  });
  const p = ALTYAZI.find(a => t >= a[0] && t < a[1]);
  const az = q('.altyazi'); az.style.display = p ? 'flex' : 'none';
  if (p && az.firstChild.textContent !== p[2]) az.firstChild.textContent = p[2];
};
"""


def main():
    haberler = haftanin_vorarlberg_haberleri()
    if not haberler:
        raise SystemExit("Bu hafta için Vorarlberg haberi bulunamadı.")
    logo = bot.veri_uri(os.path.join(bot.KOK, "assets", "logo-beyaz.png"), "image/png")
    son = dt.datetime.now()
    bas = son - dt.timedelta(days=6)
    aralik = (f"{bas.day}–{son.day} {bot.AYLAR[son.month - 1]} {son.year}" if bas.month == son.month
              else f"{bas.day} {bot.AYLAR[bas.month - 1]} – {son.day} {bot.AYLAR[son.month - 1]} {son.year}")

    z = Zaman()
    bolumler, govde = [], []
    ust = lambda sag: (f'<div class="ust"><img src="{logo}" alt="Havadis.at"><div class="sag">'
                       f'<div class="etiket">{sag}</div><div class="ki">{E(bot.KI_ETIKET)}</div></div></div>')

    # Giriş
    b0 = z.t
    z.bekle(0.6)
    z.soyle("Merhaba. Havadis ile Vorarlberg'de bu hafta. İşte haftanın öne çıkan haberleri.")
    z.bekle(0.6)
    bolumler.append((b0, z.t))
    govde.append(f'<div class="b"><img class="giris-arka" src="{foto(haberler[0]["resim"], W, H)}" alt="">'
                 f'<div class="karart"></div>{ust("Haftalık özet")}<div class="giris"><h1 class="kos">Vorarlberg’de<br>'
                 f'<span class="bant">bu hafta</span></h1><div class="aralik kos">{aralik.upper()}</div></div></div>')

    # Haberler: hedef süreye ulaşana kadar (kapanış payı ~9 sn)
    secilen = []
    for h in haberler:
        if z.t > HEDEF - 24 and len(secilen) >= 3:
            break
        secilen.append(h)
    toplam = len(secilen)
    for i, h in enumerate(secilen):
        b = z.t
        z.bekle(0.5)
        baslik = h["baslik"].rstrip(".!?") + "."
        z.soyle(baslik + " " + h.get("ozet", ""))
        z.bekle(0.5)
        bolumler.append((b, z.t))
        t = h["tarih"]
        govde.append(f'<div class="b">{ust(f"{i + 1:02d} / {toplam:02d}")}<div class="foto"><img src="{foto(h["resim"], 1080, 640)}" alt=""></div>'
                     f'<div class="bilgi"><div class="no kos"><b>{i + 1:02d}</b><span>/{toplam:02d}</span></div>'
                     f'<div class="gun kos">{karusel.GUNLER[t.weekday()]} · {t.day} {bot.AYLAR[t.month - 1]}</div>'
                     f'<h2 class="kos">{E(h["baslik"])}</h2></div></div>')
        print(f"{i + 1}. {h['baslik'][:60]} → {z.t:.1f} sn", flush=True)

    # Kapanış
    b = z.t
    z.bekle(0.4)
    z.soyle("Haberlerin tamamı havadis.at'de. Bizi takip etmeyi unutmayın. İyi haftalar.")
    z.bekle(1.5)
    bolumler.append((b, z.t))
    govde.append(f'<div class="b"><div class="kapanis"><img src="{logo}" alt="Havadis.at">'
                 f'<div class="cta kos">Haberlerin tamamı<br><span class="bant">havadis.at’de</span></div>'
                 f'<div class="takip">Takip edin: @havadis.at</div></div></div>')

    sure = z.t
    ses = os.path.join(GECICI, "ses.wav")
    sesi_birlestir(z, ses, sure)
    js = JS.replace("__BOLUMLER__", json.dumps(bolumler)).replace("__ALTYAZI__", json.dumps(z.altyazi, ensure_ascii=False))
    sayfa = (f'<!doctype html><html lang="tr"><head><meta charset="utf-8">{karusel.FONT}<style>{CSS}</style></head>'
             f'<body><div class="v">{"".join(govde)}<div class="altyazi"><span></span></div></div><script>{js}</script></body></html>')

    print(f"Toplam süre: {sure:.1f} sn, {toplam} haber, {len(z.altyazi)} altyazı parçası", flush=True)
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-i", ses, "-t", str(sure), "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-movflags", "+faststart", CIKTI], stdin=subprocess.PIPE)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        s = tarayici.new_page(viewport={"width": W, "height": H})
        s.set_content(sayfa, wait_until="networkidle", timeout=120000)
        s.evaluate("document.fonts.ready")
        s.evaluate("() => window.sigdir()")
        for i in range(int(sure * FPS)):
            s.evaluate(f"() => window.kare({i / FPS})")
            ffmpeg.stdin.write(s.screenshot(type="jpeg", quality=88))
        tarayici.close()
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError("ffmpeg video oluşturamadı")
    print("Hazır:", CIKTI)


if __name__ == "__main__":
    main()
