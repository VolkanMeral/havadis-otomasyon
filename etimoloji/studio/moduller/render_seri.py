"""Kelimelerin Gizli Tarihi – MODERN tema (Havadis renkleri).
senaryo_sesli.json'dan 1080x1920 MP4 üretir. Görseller kodla üretilir."""
import json, sys, subprocess, math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
RAQM = ImageFont.Layout.RAQM
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
DISP = "/usr/share/fonts/opentype/inter/InterDisplay-{}.otf"
ARAP_B = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
KOYU = (5, 28, 31); LACI = (10, 52, 55); KIRMIZI = (242, 179, 61); BEYAZ = (246, 240, 228); GRI = (168, 198, 192); MUREKKEP = (6, 34, 37)
LORA = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"; LORA_I = "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf"
BURADA = os.path.dirname(os.path.abspath(__file__))

_fc = {}
def font(path, size, wght=None):
    k = (path, size, wght)
    if k not in _fc:
        f = ImageFont.truetype(path, size, layout_engine=RAQM)
        if wght:
            try: f.set_variation_by_axes([wght])
            except Exception: pass
        _fc[k] = f
    return _fc[k]
def serif(size, w=700): return font(LORA, size, w)

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def eout(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def fade(t, t0, d=0.5): return ease((t - t0) / d)

# ---------------- zemin ----------------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def gradyan(ust, alt):
    y = (yy / H)[..., None]
    return np.array(ust, np.float32) * (1 - y) + np.array(alt, np.float32) * y

def isik(cx, cy, rx, ry, renk, guc):
    g = np.exp(-(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2))
    return g[..., None] * np.array(renk, np.float32) * guc

def izgara(arr, aralik=46, a=0.035):
    m = (((xx + yy) % aralik) < 1.6).astype(np.float32)[..., None]
    return arr * (1 - a * m) + 255 * a * m

def vinyet(arr, k=0.55):
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return arr * np.clip(1 - k * (d / 1.4) ** 2, 0.25, 1)[..., None]

def z_temel(ust=KOYU, alt=LACI, isiklar=(), grid=True):
    a = gradyan(ust, alt)
    for i in isiklar: a = a + isik(*i)
    if grid: a = izgara(a)
    return np.clip(vinyet(a), 0, 255).astype(np.uint8)

def kemer_katmani(acik, dolgu):
    """Neon çizgili modern kemer. acik: 0..1.4, dolgu: 0..1 iç parlaklık."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    cw = int(W * (0.16 + 0.52 * min(acik, 1.0))) + int(max(0, acik - 1) * W * 1.2)
    cx = W // 2; top, bot = int(H * 0.17), int(H * 0.80)
    if dolgu > 0:
        ic = Image.new("L", (W, H), 0); di = ImageDraw.Draw(ic)
        di.rectangle([cx - cw // 2, top + cw // 2, cx + cw // 2, bot], fill=255); di.ellipse([cx - cw // 2, top, cx + cw // 2, top + cw], fill=255)
        grad = Image.fromarray(np.clip(gradyan((252, 246, 232), (242, 186, 92)), 0, 255).astype(np.uint8)).convert("RGBA")
        grad.putalpha(ic.point(lambda v: int(v * dolgu)).filter(ImageFilter.GaussianBlur(4)))
        L = Image.alpha_composite(L, grad); d = ImageDraw.Draw(L)
    for kal, a in ((10, 70), (4, 255)):
        d.arc([cx - cw // 2, top, cx + cw // 2, top + cw], 180, 360, fill=KIRMIZI + (a,), width=kal)
        d.line([cx - cw // 2, top + cw // 2, cx - cw // 2, bot], fill=KIRMIZI + (a,), width=kal)
        d.line([cx + cw // 2, top + cw // 2, cx + cw // 2, bot], fill=KIRMIZI + (a,), width=kal)
    glow = L.filter(ImageFilter.GaussianBlur(26))
    return Image.alpha_composite(glow, L)

TEMEL = {}
def temel(ad):
    if ad not in TEMEL:
        TEMEL[ad] = {
            "gece": lambda: z_temel(KOYU, (14, 40, 38), [(W * .5, H * .78, W * .6, H * .28, KIRMIZI, .55), (W * .1, H * .15, W * .5, H * .3, (30, 140, 130), .5)]),
            "kapi": lambda: z_temel(KOYU, LACI, [(W * .5, H * .5, W * .5, H * .45, KIRMIZI, .25)]),
            "parsomen": lambda: z_temel((6, 34, 37), (12, 58, 56), [(W * .5, H * .3, W * .7, H * .35, (30, 150, 140), .55), (W * .8, H * .75, W * .5, H * .3, KIRMIZI, .35)]),
            "col": lambda: z_temel((4, 22, 30), (70, 52, 30), [(W * .5, H * .9, W * .9, H * .3, (242, 160, 60), .55)], grid=False),
            "zincir": lambda: z_temel(KOYU, LACI, [(W * .15, H * .2, W * .5, H * .4, KIRMIZI, .3), (W * .9, H * .8, W * .5, H * .4, (20, 120, 110), .4)]),
            "kunye": lambda: z_temel(KOYU, (10, 46, 48), [(W * .5, H * .4, W * .6, H * .35, KIRMIZI, .3)]),
        }[ad]()
    return TEMEL[ad]

YILDIZ = [(random.Random(i).random() * W, random.Random(i + 99).random() * H * 0.62, random.Random(i + 7).random()) for i in range(260)]

GORSEL_DIR = "."
BOLUM = 1
GORSEL = {}
KOYULUK = {"kok": (0.38, 5), "yolculuk": (0.30, 7), "giris": (0.42, 2)}
def gorsel_zemin(sahne):
    ad = sahne["gorsel"]
    if ad not in GORSEL:
        im = Image.open(os.path.join(GORSEL_DIR, ad)).convert("RGB")
        BW, BH = int(W * 1.14), int(H * 1.14)
        sc = max(BW / im.width, BH / im.height); im = im.resize((int(im.width * sc) + 1, int(im.height * sc) + 1), Image.LANCZOS)
        l, u = (im.width - BW) // 2, (im.height - BH) // 3; im = im.crop((l, u, l + BW, u + BH))
        k, blur = KOYULUK.get(sahne["id"], (0.80, 0))
        if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
        a = np.asarray(im, np.float32)
        gy = np.linspace(0, 1, BH)[:, None, None]
        renk = np.array(KOYU, np.float32)
        a = a * k * (1 - 0.6 * np.clip((gy - 0.55) / 0.45, 0, 1)) + renk * (1 - k) * 0.6   # petrol tonu + altta koyulaşma
        a = a * 0.88 + a.mean(axis=2, keepdims=True) * 0.12                                   # hafif doygunluk düşürme
        GORSEL[ad] = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return GORSEL[ad]

KEMER = {}
def zemin(sahne, t):
    z = sahne["zemin"]; p = (t - sahne["bas"]) / max(0.1, sahne["son"] - sahne["bas"])
    if sahne.get("gorsel"):
        im = gorsel_zemin(sahne); BW, BH = im.size
        z0 = 1.0 + 0.08 * ease(p); cw, ch = BW / z0 / 1.14 * 1.0, BH / z0 / 1.14
        cx = BW / 2 + (20 - 40 * p); cy = BH / 2 - 20 * p
        return im.resize((W, H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))
    if z.startswith("kapi"):
        base = Image.fromarray(temel("kapi"))
        ac, dol = {"kapi": (0.05 + 0.5 * ease(p * 1.1), 0.15 + 0.5 * ease(p)), "kapi_genis": (0.62 + 0.25 * ease(p), 0.8),
                   "kapi_isik": (0.9 + 0.55 * ease(p * 1.3), 1.0)}[z]
        key = (z, round(ac, 2), round(dol, 2))
        if key not in KEMER:
            if len(KEMER) > 4: KEMER.pop(next(iter(KEMER)))
            KEMER[key] = Image.alpha_composite(base.convert("RGBA"), kemer_katmani(ac, dol)).convert("RGB")
        im = KEMER[key]
    else:
        im = Image.fromarray(temel(z))
        if z == "col":
            d = ImageDraw.Draw(im)
            for x, y, b in YILDIZ:
                a = int(120 + 120 * math.sin(t * 2 + b * 20)); d.point((x, y), fill=(a, a, a))
            for i, (base, amp, fr, col) in enumerate([(0.74, 34, 0.006, (30, 34, 26)), (0.82, 46, 0.004, (10, 22, 22))]):
                pts = [(x, H * base + amp * math.sin(x * fr + i * 2 + t * 0.05)) for x in range(0, W + 20, 20)]
                d.polygon(pts + [(W, H), (0, H)], fill=col)
                d.line(pts, fill=KIRMIZI + (255,), width=2)
    z0 = 1.0 + 0.05 * p
    if z0 > 1.001:
        cw, ch = W / z0, H / z0
        im = im.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2 - 15 * p, (W + cw) / 2, (H + ch) / 2 - 15 * p))
    return im

# ---------------- yardımcı çizim ----------------
def ortala(d, y, s, f, fill, direction=None, x0=0, w=W):
    kw = {"direction": direction} if direction else {}
    tw = d.textlength(s, font=f, **kw); d.text((x0 + (w - tw) / 2, y), s, font=f, fill=fill, **kw)
    return tw

def harf_aralikli(d, y, s, f, fill, ara):
    ws = [d.textlength(c, font=f) for c in s]; tw = sum(ws) + ara * (len(s) - 1); x = (W - tw) / 2
    for c, cw in zip(s, ws): d.text((x, y), c, font=f, fill=fill); x += cw + ara

def cam(d, box, r=36, a=1.0):
    d.rounded_rectangle(box, r, fill=(255, 255, 255, int(20 * a)), outline=(255, 255, 255, int(46 * a)), width=2)

def hap(d, x, y, s, f, dolgu, yazi, pad=(22, 10), merkez=False):
    tw = d.textlength(s, font=f); bb = f.getbbox("ÇĞHg"); th = bb[3] - bb[1]
    if merkez: x = (W - tw) / 2 - pad[0]
    d.rounded_rectangle([x, y, x + tw + 2 * pad[0], y + th + 2 * pad[1]], (th + 2 * pad[1]) // 2, fill=dolgu)
    d.text((x + pad[0], y + pad[1] - bb[1]), s, font=f, fill=yazi)
    return tw + 2 * pad[0]

def satirla(d, kelimeler, f, maxw):
    sat = [[]]; w = 0; bos = d.textlength(" ", font=f)
    for k in kelimeler:
        kw = d.textlength(k, font=f)
        if sat[-1] and w + bos + kw > maxw: sat.append([]); w = 0
        w += (bos if sat[-1] else 0) + kw; sat[-1].append(k)
    return sat

# ---------------- MODERN ALTYAZI: renkli kutu, okundukça açılan yazı ----------------
def altyazi(L, d, sahne, t):
    akt = [a for a in sahne.get("altyazi", []) if a["t"] <= t]
    if not akt: return
    a = akt[-1]; bit = a["t"] + a.get("sure", 3) + 0.45
    if t > bit: return
    kel = a["metin"].split(); f = font(DISP.format("ExtraBold"), 54)
    # her kelimenin açılma anı: harf sayısıyla orantılı
    uz = [len(k) + 2 for k in kel]; top = sum(uz); sure = a.get("sure", 3) * 0.96
    anlar = []; acc = 0
    for u in uz: anlar.append(a["t"] + sure * acc / top); acc += u
    sat = satirla(d, kel, f, 840)
    lh = 76; bos = d.textlength(" ", font=f) * 1.5
    gor = sum(1 for x in anlar if x <= t)
    # kutu boyutu: açılan kısma göre yumuşakça büyür
    tam_w = max(sum(d.textlength(k, font=f) for k in s) + bos * (len(s) - 1) for s in sat)
    h = lh * len(sat) + 36
    giris = eout((t - a["t"]) / 0.28); cikis = 1 - ease((t - (bit - 0.3)) / 0.3)
    al = giris * cikis
    if al <= 0: return
    bw = tam_w + 64; x0 = (W - bw) / 2; y0 = 1296 - (len(sat) - 1) * lh / 2 + (1 - giris) * 26
    # gölge + kırmızı kutu
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([x0, y0 + 10, x0 + bw, y0 + h + 10], 30, fill=(0, 0, 0, int(140 * al)))
    L.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    ters = sahne["zemin"] in ("kapi_genis", "kapi_isik")  # açık zeminde koyu kutu
    KUTU, YAZI, VURGU_Z, VURGU_Y = (MUREKKEP, BEYAZ, KIRMIZI, MUREKKEP) if ters else (KIRMIZI, MUREKKEP, MUREKKEP, KIRMIZI)
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + h], 30, fill=KUTU + (int(245 * al),))
    idx = 0; y = y0 + 18
    for s in sat:
        sw = sum(d.textlength(k, font=f) for k in s) + bos * (len(s) - 1); x = (W - sw) / 2
        for k in s:
            p = (t - anlar[idx]) / 0.18
            if p <= 0:
                d.text((x, y), k, font=f, fill=YAZI + (int(80 * al),))   # henüz okunmadı: soluk
            else:
                aa = int(255 * al * min(1, 0.35 + p))
                aktif = idx == gor - 1 and t < anlar[idx] + 0.55
                if aktif:  # o an okunan kelime: beyaz vurgu kutusu, kırmızı yazı
                    kw = d.textlength(k, font=f); bb = f.getbbox(k)
                    d.rounded_rectangle([x - 10, y + bb[1] - 8, x + kw + 10, y + bb[3] + 10], 14, fill=VURGU_Z + (int(255 * al),))
                    d.text((x, y), k, font=f, fill=VURGU_Y + (int(255 * al),))
                else:
                    d.text((x, y), k, font=f, fill=YAZI + (aa,))
            x += d.textlength(k, font=f) + bos; idx += 1
        y += lh

def kredi(d, sahne, t):
    if not sahne.get("kredi"): return
    a = min(fade(t, sahne["bas"] + 0.4, 0.4), 1 - fade(t, sahne["son"] - 0.3, 0.3))
    if a <= 0: return
    f = font(INTER.format("Medium"), 21); s = "Görsel (temsilî): " + sahne["kredi"]
    while d.textlength(s, font=f) > 900: s = s[:-2]
    y = 1630 if sahne.get("kaynak") else 1580
    ortala(d, y, s, f, (255, 255, 255, int(150 * a)))

def kaynak(d, sahne, t):
    if "kaynak" not in sahne: return
    a = min(fade(t, sahne["bas"] + 0.6, 0.4), 1 - fade(t, sahne["son"] - 0.35, 0.35))
    if a <= 0: return
    f = font(INTER.format("Medium"), 26); fb = font(INTER.format("Bold"), 22)
    s = sahne["kaynak"]; maxw = 700
    while d.textlength(s, font=f) > maxw: s = s[:-2]
    if s != sahne["kaynak"]: s = s.rstrip() + "…"
    tw = d.textlength(s, font=f); lw = d.textlength("KAYNAK", font=fb)
    bw = lw + tw + 76; x0 = (W - bw) / 2; y0 = 1560
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + 56], 28, fill=(4, 24, 27, int(205 * a)), outline=(255, 255, 255, int(50 * a)), width=2)
    d.rounded_rectangle([x0 + 8, y0 + 8, x0 + 8 + lw + 28, y0 + 48], 20, fill=KIRMIZI + (int(255 * a),))
    d.text((x0 + 22, y0 + 15), "KAYNAK", font=fb, fill=MUREKKEP + (int(255 * a),))
    d.text((x0 + lw + 54, y0 + 13), s, font=f, fill=BEYAZ + (int(225 * a),))

# ---------------- büyük öğeler ----------------
def buyukler(L, d, sahne, t):
    for b in sahne.get("buyuk", []):
        a = min(fade(t, b["t"], 0.55), 1 - fade(t, sahne["son"] - 0.3, 0.3))
        if b["stil"] == "acilis": a = 1.0
        if a <= 0: continue
        A = int(255 * a); st = b["stil"]; up = (1 - eout((t - b["t"]) / 0.7)) * 50
        if st == "acilis":   # ilk kareden itibaren tam görünür marka + kelime
            A0 = int(255 * (1 - fade(t, sahne["son"] - 0.3, 0.3)))
            d.rounded_rectangle([90, 300, W - 90, 560], 40, fill=(3, 18, 20, int(A0 * .82)), outline=KIRMIZI + (int(A0 * .9),), width=3)
            hap(d, 0, 276, f"BÖLÜM {BOLUM}", font(INTER.format("Bold"), 28), KIRMIZI + (A0,), MUREKKEP + (A0,), merkez=True)
            harf_aralikli(d, 350, "KELİMELERİN", font(INTER.format("Bold"), 44), KIRMIZI + (A0,), 10)
            ortala(d, 408, "Gizli Tarihi", serif(116, 700), BEYAZ + (A0,))
            nab = 1 + 0.025 * math.sin(t * 3)
            f = serif(int(190 * nab), 700); ortala(d, 760 - (nab - 1) * 120, b["metin"], f, BEYAZ + (A0,))
            lw = 360; d.rounded_rectangle([W / 2 - lw / 2, 990, W / 2 + lw / 2, 1002], 6, fill=KIRMIZI + (A0,))
            if "arapca" in sahne: ortala(d, 1020, sahne["arapca"], font(ARAP_B, 96), KIRMIZI + (A0,), "rtl")
            continue
        if st == "dev":
            f = serif(176, 700)
            # harf harf düşen kinetik başlık
            s = b["metin"]; ws = [d.textlength(c, font=f) for c in s]; tw = sum(ws) + 8 * (len(s) - 1); x = (W - tw) / 2
            for i, (c, cw) in enumerate(zip(s, ws)):
                pa = eout((t - b["t"] - i * 0.06) / 0.5)
                if pa > 0: d.text((x, 720 + (1 - pa) * 80), c, font=f, fill=BEYAZ + (int(A * pa),))
                x += cw + 8
            lw = 420 * eout((t - b["t"] - 0.6) / 0.6)
            d.rounded_rectangle([W / 2 - lw / 2, 930, W / 2 + lw / 2, 942], 6, fill=KIRMIZI + (A,))
        elif st == "arapca":
            cam(d, [140, 330 + up, W - 140, 760 + up], 48, a)
            ortala(d, 380 + up, b["metin"], font(ARAP_B, 220), BEYAZ + (A,), "rtl")
        elif st == "translit":
            ortala(d, 660 + up, b["metin"], font(LORA_I, 64, 500), GRI + (A,))
        elif st == "kok_ar":
            ortala(d, 820 + up, b["metin"], font(ARAP_B, 150), KIRMIZI + (A,), "rtl")
        elif st == "kok_tr":
            f = font(DISP.format("Bold"), 40)
            g1, g2 = (b["metin"].split("|") + [""])[:2] if "|" in b["metin"] else ("KÖK  r-ḥ-b", "genişlik · bolluk")
            while d.textlength(g1, font=f) + d.textlength(g2, font=f) + 108 > W - 120 and f.size > 26: f = font(DISP.format("Bold"), f.size - 2)
            w1 = d.textlength(g1, font=f) + 44; w2 = d.textlength(g2, font=f) + 44; x = (W - w1 - w2 - 20) / 2
            hap(d, x, 1040 + up, g1, f, KIRMIZI + (A,), MUREKKEP + (A,))
            hap(d, x + w1 + 20, 1040 + up, g2, f, (255, 255, 255, int(A * .12)), BEYAZ + (A,))
        elif st == "alinti":
            d.rounded_rectangle([110, 520 + up, W - 110, 900 + up], 44, fill=(4, 24, 27, int(220 * a)), outline=(255, 255, 255, int(40 * a)), width=2)
            hap(d, 0, 494 + up, b.get("etiket", "ESKİ SÖZLÜKLERE GÖRE"), font(INTER.format("Bold"), 26), KIRMIZI + (A,), MUREKKEP + (A,), merkez=True)
            satir = b["metin"].replace("“", "").replace("”", "").split("\n"); y = 700 - len(satir) * 46 + up
            for s in satir:
                ortala(d, y, s, font(LORA_I, 66, 600), BEYAZ + (A,)); y += 92
        elif st == "etiket":
            hap(d, 0, 540 + up, b["metin"], font(DISP.format("Bold"), 36), KIRMIZI + (A,), MUREKKEP + (A,), merkez=True)
        elif st == "isim":
            d.rounded_rectangle([110, 606 + up, W - 110, 850 + up], 40, fill=(3, 18, 20, int(205 * a)), outline=KIRMIZI + (int(110 * a),), width=2)
            fs_ = 108
            while d.textlength(b["metin"], font=serif(fs_, 700)) > W - 260 and fs_ > 60: fs_ -= 4
            ortala(d, 620 + (108 - fs_) * 0.5 + up, b["metin"], serif(fs_, 700), BEYAZ + (A,))
        elif st == "alt_isim":
            ortala(d, 775 + up, b["metin"], font(INTER.format("Medium"), 46), GRI + (A,))
        elif st == "uyari_alt":
            f = font(INTER.format("Bold"), 26); s = b["metin"]; tw = d.textlength(s, font=f)
            d.rounded_rectangle([(W - tw) / 2 - 24, 1130, (W + tw) / 2 + 24, 1182], 26, fill=(3, 18, 20, int(A * .8)), outline=(255, 255, 255, int(A * .7)), width=2)
            ortala(d, 1142, s, f, (255, 255, 255, int(A * .9)))
        elif st == "uyari":
            f = font(INTER.format("Bold"), 26); s = b["metin"]; tw = d.textlength(s, font=f)
            d.rounded_rectangle([(W - tw) / 2 - 24, 880, (W + tw) / 2 + 24, 932], 26, outline=(255, 255, 255, int(A * .7)), width=2)
            ortala(d, 892, s, f, (255, 255, 255, int(A * .85)))
        elif st == "final":
            y = 620 + up
            for s in b["metin"].split("\n"):
                fz = 136
                while d.textlength(s, font=serif(fz, 700)) > W - 200 and fz > 70: fz -= 4
                ortala(d, y, s, serif(fz, 700), MUREKKEP + (A,)); y += 156

def zincir(d, sahne, t):
    y = 280
    for i, z in enumerate(sahne["zincir"]):
        a = min(fade(t, z["t"], 0.5), 1 - fade(t, sahne["son"] - 0.3, 0.3))
        if a > 0:
            A = int(255 * a); off = (1 - eout((t - z["t"]) / 0.6)) * 80
            if i < len(sahne["zincir"]) - 1:
                ln = 64 * eout((t - z["t"] - 0.3) / 0.5)
                d.rounded_rectangle([W / 2 - 3, y + 172, W / 2 + 3, y + 172 + ln * 0.75], 3, fill=KIRMIZI + (A,))
            cam(d, [100 + off, y, W - 100 + off, y + 172], 36, a)
            d.text((150 + off, y + 24), z["dil"], font=font(INTER.format("Bold"), 26), fill=KIRMIZI + (A,))
            d.text((150 + off, y + 60), z["kelime"], font=serif(76, 700), fill=BEYAZ + (A,))
            if z["yazi"]:
                f = font(ARAP_B, 80); tw = d.textlength(z["yazi"], font=f, direction="rtl")
                d.text((W - 150 - tw + off, y + 44), z["yazi"], font=f, fill=BEYAZ + (int(A * .75),), direction="rtl")
        y += 220

LOGO = {k: Image.open(f"{BURADA}/../assets/logo-{k}.png").convert("RGBA") for k in ("beyaz",)}
def logo(w, alpha=1.0):
    im = LOGO["beyaz"]; im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    if alpha < 1: im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    return im

def kunye(L, d, sahne, t):
    a = fade(t, sahne["bas"], 0.5); A = int(255 * a)
    hap(d, 0, 380, "KELİMELERİN", font(INTER.format("Bold"), 30), KIRMIZI + (A,), MUREKKEP + (A,), merkez=True)
    ortala(d, 446, "Gizli Tarihi", serif(128, 700), BEYAZ + (A,))
    ortala(d, 612, "Her kelimenin bir hikâyesi var.", font(LORA_I, 44, 500), GRI + (A,))
    a1 = fade(t, sahne["bas"] + 0.7, 0.5); A1 = int(255 * a1)
    cam(d, [90, 740, W - 90, 1250], 36, a1)
    d.text((130, 780), "KAYNAKÇA", font=font(INTER.format("Bold"), 26), fill=KIRMIZI + (A1,))
    y = 830; f = font(INTER.format("Regular"), 27)
    for k in sahne["kaynakca"]:
        words = k.split(); line = ""
        for w_ in words:
            if d.textlength(line + " " + w_, font=f) > 800 and line: d.text((130, y), line, font=f, fill=BEYAZ + (int(A1 * .85),)); y += 38; line = w_
            else: line = (line + " " + w_).strip()
        d.text((130, y), line, font=f, fill=BEYAZ + (int(A1 * .85),)); y += 52
    a2 = fade(t, sahne["bas"] + 1.2, 0.5)
    if a2 > 0:
        lg = logo(360, a2); L.alpha_composite(lg, ((W - lg.width) // 2, 1350))
        ortala(d, 1350 + lg.height + 24, "havadis.at", font(INTER.format("SemiBold"), 32), GRI + (int(255 * a2),))

CER_KAL, CER_IC, CER_R = 12, 22, 56
def _cerceve():
    i, r = CER_IC, CER_R; x0, y0, x1, y1 = i, i, W - i, H - i
    pts = [(W / 2, y0)]
    def yay(cx, cy, a0, a1):
        for k in range(1, 13):
            a = math.radians(a0 + (a1 - a0) * k / 12); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts.append((x1 - r, y0)); yay(x1 - r, y0 + r, -90, 0)
    pts.append((x1, y1 - r)); yay(x1 - r, y1 - r, 0, 90)
    pts.append((x0 + r, y1)); yay(x0 + r, y1 - r, 90, 180)
    pts.append((x0, y0 + r)); yay(x0 + r, y0 + r, 180, 270)
    pts.append((W / 2, y0))
    cum = [0.0]
    for a, b in zip(pts, pts[1:]): cum.append(cum[-1] + math.dist(a, b))
    return pts, np.array(cum)
CERCEVE = _cerceve()

def _marka(d, f1, f2, f3, x1):
    gw = max(d.textlength("Gizli Tarihi", font=f2), d.textlength(f"BÖLÜM {BOLUM} · TASLAK", font=f3))
    d.rounded_rectangle([x1 - gw - 24, 88, x1 + 16, 198], 22, fill=(3, 18, 20, 200), outline=KIRMIZI + (150,), width=2)
    d.text((x1 - d.textlength("KELİMELERİN", font=f1), 98), "KELİMELERİN", font=f1, fill=KIRMIZI + (255,))
    d.text((x1 - d.textlength("Gizli Tarihi", font=f2), 122), "Gizli Tarihi", font=f2, fill=BEYAZ + (240,))
    d.text((x1 - d.textlength(f"BÖLÜM {BOLUM} · TASLAK", font=f3), 166), f"BÖLÜM {BOLUM} · TASLAK", font=f3, fill=GRI + (200,))

def ust_bant(L, d, t, sure, acik_logo=True, marka=True):
    if acik_logo:  # logo: koyu rozet içinde, belirgin ama ölçülü
        lg = logo(196); px, py = 26, 20
        d.rounded_rectangle([56, 92, 56 + lg.width + 2 * px, 92 + lg.height + 2 * py], 22,
                            fill=(3, 18, 20, 215), outline=KIRMIZI + (150,), width=2)
        L.alpha_composite(lg, (56 + px, 92 + py))
    f1 = font(INTER.format("Bold"), 21); f2 = font(LORA_I, 34, 600); f3 = font(INTER.format("SemiBold"), 20)
    x1 = W - 60
    if marka: _marka(d, f1, f2, f3, x1)
    # ilerleme çerçevesi: üst ortadan başlayıp saat yönünde tüm ekranı dolaşır
    pts, cum = CERCEVE
    d.line(pts + [pts[0]], fill=(255, 255, 255, 40), width=CER_KAL, joint="curve")
    hedef = cum[-1] * min(1.0, t / sure)
    n = int(np.searchsorted(cum, hedef))
    if n > 0:
        yol = pts[:n]
        if n < len(pts):
            r = (hedef - cum[n - 1]) / max(1e-6, cum[n] - cum[n - 1])
            yol = yol + [(pts[n - 1][0] + (pts[n][0] - pts[n - 1][0]) * r, pts[n - 1][1] + (pts[n][1] - pts[n - 1][1]) * r)]
        if len(yol) > 1:
            d.line(yol, fill=KIRMIZI + (255,), width=CER_KAL, joint="curve")
            x, y = yol[-1]; d.ellipse([x - CER_KAL, y - CER_KAL, x + CER_KAL, y + CER_KAL], fill=(255, 255, 255, 255))

GRAIN = [(np.random.default_rng(i).normal(0, 5, (H, W, 1))).astype(np.float32) for i in range(4)]

def kare(sen, t, gecis=0.35):
    sah = sen["sahneler"]
    cur = next((s for s in sah if s["bas"] <= t < s["son"]), sah[-1]); i = sah.index(cur)
    bg = zemin(cur, t)
    if i > 0 and t - cur["bas"] < gecis:
        o = sah[i - 1]; bg = Image.blend(zemin(o, o["son"] - 0.01), bg, ease((t - cur["bas"]) / gecis))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    buyukler(L, d, cur, t)
    if cur["zemin"] == "zincir": zincir(d, cur, t)
    if cur["zemin"] == "kunye": kunye(L, d, cur, t)
    altyazi(L, d, cur, t); kaynak(d, cur, t); kredi(d, cur, t); ust_bant(L, d, t, sen["sure"], cur["zemin"] != "kunye", cur["id"] != "giris")
    out = Image.alpha_composite(bg.convert("RGBA"), L).convert("RGB")
    arr = np.asarray(out, np.float32) + GRAIN[int(t * FPS) % 4]
    return np.clip(arr, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    sen = json.load(open(sys.argv[1])); muzik = sys.argv[2]; cikis = sys.argv[3]
    GORSEL_DIR = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "gorsel")
    BOLUM = sen.get("bolum", 1)
    if len(sys.argv) > 4 and sys.argv[4] == "kapak":
        k = json.loads(json.dumps(sen)); k["sahneler"][0]["altyazi"] = []
        Image.fromarray(kare(k, 0.0)).save(cikis, quality=92); sys.exit()
    if len(sys.argv) > 4:
        for ts in sys.argv[4:]: Image.fromarray(kare(sen, float(ts))).save(f"{cikis}_{ts}.jpg", quality=88)
        sys.exit()
    n = int(sen["sure"] * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-i", muzik, "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cikis], stdin=subprocess.PIPE)
    for k in range(n):
        ff.stdin.write(kare(sen, k / FPS).tobytes())
        if k % 300 == 0: print(f"{k}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
