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
KOYU = (7, 11, 20); LACI = (14, 26, 51); KIRMIZI = (228, 35, 32); BEYAZ = (245, 243, 239); GRI = (150, 160, 178)
BURADA = os.path.dirname(os.path.abspath(__file__))

_fc = {}
def font(path, size):
    k = (path, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(path, size, layout_engine=RAQM)
    return _fc[k]

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

def izgara(arr, aralik=90, a=0.05):
    arr = arr.copy()
    arr[:, ::aralik] = arr[:, ::aralik] * (1 - a) + 255 * a
    arr[::aralik, :] = arr[::aralik, :] * (1 - a) + 255 * a
    return arr

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
        grad = Image.fromarray(np.clip(gradyan((255, 236, 214), (255, 120, 90)), 0, 255).astype(np.uint8)).convert("RGBA")
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
            "gece": lambda: z_temel(KOYU, (20, 14, 30), [(W * .5, H * .78, W * .6, H * .28, KIRMIZI, .55), (W * .1, H * .15, W * .5, H * .3, (40, 70, 160), .5)]),
            "kapi": lambda: z_temel(KOYU, LACI, [(W * .5, H * .5, W * .5, H * .45, KIRMIZI, .25)]),
            "parsomen": lambda: z_temel((10, 16, 34), (24, 18, 40), [(W * .5, H * .3, W * .7, H * .35, (60, 90, 200), .55), (W * .8, H * .75, W * .5, H * .3, KIRMIZI, .35)]),
            "col": lambda: z_temel((8, 10, 30), (90, 30, 40), [(W * .5, H * .9, W * .9, H * .3, (255, 120, 60), .55)], grid=False),
            "zincir": lambda: z_temel(KOYU, LACI, [(W * .15, H * .2, W * .5, H * .4, KIRMIZI, .3), (W * .9, H * .8, W * .5, H * .4, (50, 90, 200), .4)]),
            "kunye": lambda: z_temel(KOYU, (12, 18, 36), [(W * .5, H * .4, W * .6, H * .35, KIRMIZI, .3)]),
        }[ad]()
    return TEMEL[ad]

YILDIZ = [(random.Random(i).random() * W, random.Random(i + 99).random() * H * 0.62, random.Random(i + 7).random()) for i in range(260)]

KEMER = {}
def zemin(sahne, t):
    z = sahne["zemin"]; p = (t - sahne["bas"]) / max(0.1, sahne["son"] - sahne["bas"])
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
            for i, (base, amp, fr, col) in enumerate([(0.74, 34, 0.006, (40, 14, 30)), (0.82, 46, 0.004, (18, 8, 18))]):
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
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + h], 30, fill=KIRMIZI + (int(245 * al),))
    idx = 0; y = y0 + 18
    for s in sat:
        sw = sum(d.textlength(k, font=f) for k in s) + bos * (len(s) - 1); x = (W - sw) / 2
        for k in s:
            p = (t - anlar[idx]) / 0.18
            if p <= 0:
                d.text((x, y), k, font=f, fill=(255, 255, 255, int(70 * al)))   # henüz okunmadı: soluk
            else:
                aa = int(255 * al * min(1, 0.35 + p))
                aktif = idx == gor - 1 and t < anlar[idx] + 0.55
                if aktif:  # o an okunan kelime: beyaz vurgu kutusu, kırmızı yazı
                    kw = d.textlength(k, font=f); bb = f.getbbox(k)
                    d.rounded_rectangle([x - 10, y + bb[1] - 8, x + kw + 10, y + bb[3] + 10], 14, fill=(255, 255, 255, int(255 * al)))
                    d.text((x, y), k, font=f, fill=KIRMIZI + (int(255 * al),))
                else:
                    d.text((x, y), k, font=f, fill=(255, 255, 255, aa))
            x += d.textlength(k, font=f) + bos; idx += 1
        y += lh

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
    d.rounded_rectangle([x0, y0, x0 + bw, y0 + 56], 28, fill=(10, 14, 26, int(200 * a)), outline=(255, 255, 255, int(50 * a)), width=2)
    d.rounded_rectangle([x0 + 8, y0 + 8, x0 + 8 + lw + 28, y0 + 48], 20, fill=KIRMIZI + (int(255 * a),))
    d.text((x0 + 22, y0 + 15), "KAYNAK", font=fb, fill=(255, 255, 255, int(255 * a)))
    d.text((x0 + lw + 54, y0 + 13), s, font=f, fill=BEYAZ + (int(225 * a),))

# ---------------- büyük öğeler ----------------
def buyukler(L, d, sahne, t):
    for b in sahne.get("buyuk", []):
        a = min(fade(t, b["t"], 0.55), 1 - fade(t, sahne["son"] - 0.3, 0.3))
        if a <= 0: continue
        A = int(255 * a); st = b["stil"]; up = (1 - eout((t - b["t"]) / 0.7)) * 50
        if st == "dev":
            f = font(DISP.format("Black"), 170)
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
            ortala(d, 660 + up, b["metin"], font(INTER.format("MediumItalic"), 60), GRI + (A,))
        elif st == "kok_ar":
            ortala(d, 820 + up, b["metin"], font(ARAP_B, 150), KIRMIZI + (A,), "rtl")
        elif st == "kok_tr":
            f = font(DISP.format("Bold"), 40); g1 = "KÖK  r-ḥ-b"; g2 = "genişlik · bolluk"
            w1 = d.textlength(g1, font=f) + 44; w2 = d.textlength(g2, font=f) + 44; x = (W - w1 - w2 - 20) / 2
            hap(d, x, 1040 + up, g1, f, KIRMIZI + (A,), (255, 255, 255, A))
            hap(d, x + w1 + 20, 1040 + up, g2, f, (255, 255, 255, int(A * .12)), BEYAZ + (A,))
        elif st == "alinti":
            d.rounded_rectangle([110, 520 + up, W - 110, 900 + up], 44, fill=(10, 14, 26, int(215 * a)), outline=(255, 255, 255, int(40 * a)), width=2)
            hap(d, 0, 494 + up, "ESKİ SÖZLÜKLERE GÖRE", font(INTER.format("Bold"), 26), KIRMIZI + (A,), (255, 255, 255, A), merkez=True)
            y = 600 + up
            for s in b["metin"].replace("“", "").replace("”", "").split("\n"):
                ortala(d, y, s, font(DISP.format("Bold"), 68), BEYAZ + (A,)); y += 92
        elif st == "etiket":
            hap(d, 0, 540 + up, b["metin"], font(DISP.format("Bold"), 36), KIRMIZI + (A,), (255, 255, 255, A), merkez=True)
        elif st == "isim":
            ortala(d, 630 + up, b["metin"], font(DISP.format("Black"), 108), BEYAZ + (A,))
        elif st == "alt_isim":
            ortala(d, 775 + up, b["metin"], font(INTER.format("Medium"), 46), GRI + (A,))
        elif st == "uyari":
            f = font(INTER.format("Bold"), 26); s = b["metin"]; tw = d.textlength(s, font=f)
            d.rounded_rectangle([(W - tw) / 2 - 24, 880, (W + tw) / 2 + 24, 932], 26, outline=(255, 255, 255, int(A * .7)), width=2)
            ortala(d, 892, s, f, (255, 255, 255, int(A * .85)))
        elif st == "final":
            y = 620 + up
            for s in b["metin"].split("\n"):
                ortala(d, y, s, font(DISP.format("Black"), 132), KOYU + (A,)); y += 150

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
            d.text((150 + off, y + 60), z["kelime"], font=font(DISP.format("Black"), 78), fill=BEYAZ + (A,))
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
    hap(d, 0, 380, "KELİMELERİN", font(INTER.format("Bold"), 30), KIRMIZI + (A,), (255, 255, 255, A), merkez=True)
    ortala(d, 450, "Gizli Tarihi", font(DISP.format("Black"), 124), BEYAZ + (A,))
    ortala(d, 610, "Her kelimenin bir hikâyesi var.", font(INTER.format("Medium"), 42), GRI + (A,))
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

def ust_bant(L, d, t, sure, acik_logo=True):
    if acik_logo: L.alpha_composite(logo(176), (64, 108))
    f = font(INTER.format("Bold"), 22); s = "KELİMELERİN GİZLİ TARİHİ"
    tw = d.textlength(s, font=f)
    d.text((W - 64 - tw, 112), s, font=f, fill=(255, 255, 255, 200))
    d.text((W - 64 - d.textlength("#1 · TASLAK", font=f), 142), "#1 · TASLAK", font=f, fill=KIRMIZI + (255,))
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
    if i == 0: bg = Image.blend(Image.new("RGB", (W, H), KOYU), bg, ease(t / 0.6))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    buyukler(L, d, cur, t)
    if cur["zemin"] == "zincir": zincir(d, cur, t)
    if cur["zemin"] == "kunye": kunye(L, d, cur, t)
    altyazi(L, d, cur, t); kaynak(d, cur, t); ust_bant(L, d, t, sen["sure"], cur["zemin"] != "kunye")
    out = Image.alpha_composite(bg.convert("RGBA"), L).convert("RGB")
    arr = np.asarray(out, np.float32) + GRAIN[int(t * FPS) % 4]
    return np.clip(arr, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    sen = json.load(open(sys.argv[1])); muzik = sys.argv[2]; cikis = sys.argv[3]
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
