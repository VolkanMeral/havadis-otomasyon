"""Kelimelerin Gizli Tarihi – senaryo.json'dan 1080x1920 MP4 üretir (taslak motoru).
Görseller kodla (procedural) üretilir; AI görüntü/sunucu katmanı sonraki aşamada eklenecek."""
import json, sys, subprocess, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
RAQM = ImageFont.Layout.RAQM
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
LORA = "/usr/share/fonts/truetype/google-fonts/Lora-Variable.ttf"
LORA_I = "/usr/share/fonts/truetype/google-fonts/Lora-Italic-Variable.ttf"
ARAP = "/usr/share/fonts/truetype/freefont/FreeSerif.ttf"
ARAP_B = "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf"
KREM = (242, 232, 213); ALTIN = (201, 164, 92); MUREKKEP = (48, 30, 16)

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

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def fade(t, t0, d=0.6): return ease((t - t0) / d)

def noise(w, h, scale, seed):
    rng = np.random.default_rng(seed)
    small = rng.random((max(2, h // scale), max(2, w // scale))).astype(np.float32)
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255

def vignette(w, h, k=1.25):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((x - w / 2) / (w / 2)) ** 2 + ((y - h / 2) / (h / 2)) ** 2)
    return np.clip(1.15 - (d / k) ** 2 * 0.85, 0.15, 1)[..., None]

# ---------- zeminler (W*1.12 boyutunda, Ken Burns için) ----------
BW, BH = int(W * 1.12), int(H * 1.12)
VIG = vignette(BW, BH)

def z_gece():
    y = np.linspace(0, 1, BH)[:, None, None]
    top = np.array([12, 12, 22], np.float32); bot = np.array([46, 28, 14], np.float32)
    img = top * (1 - y) + bot * y + np.zeros((BH, BW, 3), np.float32)
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    glow = np.exp(-(((xx - BW * 0.5) / (BW * 0.55)) ** 2 + ((yy - BH * 0.78) / (BH * 0.3)) ** 2))
    img += glow[..., None] * np.array([120, 70, 25], np.float32)
    img *= (0.85 + 0.3 * noise(BW, BH, 90, 1))[..., None]
    return np.clip(img * VIG, 0, 255)

def duvar(seed):
    n = noise(BW, BH, 40, seed) * 0.6 + noise(BW, BH, 9, seed + 1) * 0.4
    img = (np.array([38, 27, 19], np.float32) * (0.6 + 0.7 * n[..., None]))
    for yb in range(0, BH, 118):  # taş sıraları
        img[yb:yb + 4] *= 0.55
    return img

def kapi_maske(acik):
    """acik: 0..1 kapı genişliği; kemerli açıklık maskesi"""
    m = Image.new("L", (BW, BH), 0); d = ImageDraw.Draw(m)
    cw = int(BW * (0.10 + 0.62 * acik)); cx = BW // 2
    top, bot = int(BH * 0.20), int(BH * 0.80)
    d.rectangle([cx - cw // 2, top + cw // 2, cx + cw // 2, bot], fill=255)
    d.ellipse([cx - cw // 2, top, cx + cw // 2, top + cw], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(6)), np.float32)[..., None] / 255

_duvar = None
def z_kapi(acik):
    global _duvar
    if _duvar is None: _duvar = duvar(5)
    m = kapi_maske(acik)
    yy = np.linspace(0, 1, BH)[:, None, None]
    isik = np.array([255, 214, 150], np.float32) * (0.75 + 0.25 * (1 - yy)) + np.zeros((BH, BW, 3), np.float32)
    img = _duvar * (1 - m) + isik * m
    # kapıdan taşan ışık
    yy2, xx2 = np.mgrid[0:BH, 0:BW].astype(np.float32)
    halo = np.exp(-(((xx2 - BW / 2) / (BW * (0.18 + 0.5 * acik))) ** 2 + ((yy2 - BH * 0.55) / (BH * 0.45)) ** 2))
    img += halo[..., None] * np.array([90, 55, 20], np.float32) * (0.5 + acik)
    # zemine düşen ışık şeridi
    floor = (yy2 > BH * 0.8) * np.exp(-((xx2 - BW / 2) / (BW * (0.12 + 0.45 * acik))) ** 2) * np.clip((BH - yy2) / (BH * 0.2), 0, 1)
    img += floor[..., None] * np.array([110, 75, 35], np.float32)
    return np.clip(img * VIG, 0, 255)

def z_parsomen():
    n = noise(BW, BH, 60, 11) * 0.5 + noise(BW, BH, 12, 12) * 0.3 + noise(BW, BH, 3, 13) * 0.2
    img = np.array([214, 188, 140], np.float32) * (0.78 + 0.35 * n[..., None])
    for y in range(int(BH * 0.18), int(BH * 0.85), 64):  # silik satır çizgileri
        img[y:y + 2] *= 0.93
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    mum = np.exp(-(((xx - BW * 0.3) / (BW * 0.7)) ** 2 + ((yy - BH * 0.35) / (BH * 0.6)) ** 2))
    img *= (0.45 + 0.75 * mum)[..., None]
    return np.clip(img * vignette(BW, BH, 1.05), 0, 255)

def z_col():
    y = np.linspace(0, 1, BH)[:, None, None]
    sky = np.array([10, 12, 30], np.float32) * (1 - y) + np.array([120, 62, 40], np.float32) * y
    img = sky + np.zeros((BH, BW, 3), np.float32)
    rng = np.random.default_rng(3)
    for _ in range(420):
        x, yy = rng.integers(0, BW), rng.integers(0, int(BH * 0.55)); b = rng.random() * 200 + 40
        img[yy:yy + 2, x:x + 2] = np.maximum(img[yy:yy + 2, x:x + 2], b)
    xs = np.arange(BW)
    for i, (base, amp, fr, col) in enumerate([(0.70, 40, 0.004, (60, 30, 20)), (0.76, 55, 0.003, (36, 18, 12)), (0.84, 35, 0.006, (18, 10, 8))]):
        h = (BH * base + amp * np.sin(xs * fr + i * 2) + amp * 0.5 * np.sin(xs * fr * 2.7 + i)).astype(int)
        for x in xs:
            img[h[x]:, x] = col
    return np.clip(img * VIG, 0, 255)

def z_koyu():
    n = noise(BW, BH, 70, 21)
    img = np.array([20, 16, 12], np.float32) * (0.7 + 0.6 * n[..., None])
    yy, xx = np.mgrid[0:BH, 0:BW].astype(np.float32)
    g = np.exp(-(((xx - BW / 2) / (BW * 0.6)) ** 2 + ((yy - BH * 0.45) / (BH * 0.4)) ** 2))
    img += g[..., None] * np.array([45, 30, 12], np.float32)
    return np.clip(img * VIG, 0, 255)

# ---------- yardımcılar ----------
GRAIN = [(np.random.default_rng(i).normal(0, 9, (H, W, 1))).astype(np.float32) for i in range(6)]

def kenburns(arr, p, zoom=(1.0, 1.08), pan=(0, -30)):
    z = zoom[0] + (zoom[1] - zoom[0]) * p
    cw, ch = BW / z / 1.12 * 1.0, BH / z / 1.12
    cx = BW / 2 + pan[0] * p; cy = BH / 2 + pan[1] * p
    im = Image.fromarray(arr.astype(np.uint8))
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return im.resize((W, H), Image.BILINEAR, box=box)

def metin_w(d, s, f): return d.textlength(s, font=f)

def ortala(d, y, s, f, fill, direction=None):
    kw = {"direction": direction} if direction else {}
    w = d.textlength(s, font=f, **kw)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, **kw)

def golge(layer, r=10, a=170):
    al = layer.split()[3].filter(ImageFilter.GaussianBlur(r))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0)); sh.putalpha(al.point(lambda v: v * a // 255))
    return sh

def satirla(d, s, f, maxw):
    kel = s.split(); sat = []; cur = ""
    for k in kel:
        t = (cur + " " + k).strip()
        if d.textlength(t, font=f) > maxw and cur: sat.append(cur); cur = k
        else: cur = t
    if cur: sat.append(cur)
    return sat

# ---------- katmanlar ----------
def altyazi(d, sahne, t):
    akt = [a for a in sahne.get("altyazi", []) if a["t"] <= t]
    if not akt: return
    a = akt[-1]; i = sahne["altyazi"].index(a)
    bit = sahne["altyazi"][i + 1]["t"] if i + 1 < len(sahne["altyazi"]) else sahne["son"]
    if "sure" in a: bit = min(bit, a["t"] + a["sure"] + 0.35)
    if t > bit - 0.05: return
    f = font(INTER.format("SemiBold"), 50)
    sat = satirla(d, a["metin"], f, 900)
    kel_say = len(a["metin"].split()); hiz = (a["sure"] / kel_say) if "sure" in a else 0.24
    gor = int((t - a["t"]) / hiz) + 1
    alpha = int(255 * min(fade(t, a["t"], 0.25), 1 - fade(t, bit - 0.25, 0.25)))
    y0 = 1360 - (len(sat) - 1) * 66; idx = 0
    for s in sat:
        ks = s.split(); tw = d.textlength(s, font=f); x = (W - tw) / 2
        for k in ks:
            if idx < gor:
                renk = ALTIN if idx == gor - 1 and gor <= kel_say else KREM
                d.text((x, y0), k, font=f, fill=renk + (alpha,))
            x += d.textlength(k + " ", font=f); idx += 1
        y0 += 66

def kaynak(d, sahne, t):
    if "kaynak" not in sahne: return
    a = int(230 * min(fade(t, sahne["bas"] + 0.8, 0.5), 1 - fade(t, sahne["son"] - 0.4, 0.4)))
    if a <= 0: return
    f = font(INTER.format("Medium"), 27); fb = font(INTER.format("Bold"), 27)
    sat = satirla(d, sahne["kaynak"], f, 820)
    y = 1520
    d.rectangle([90, y + 4, 95, y + 4 + 38 * len(sat) - 6], fill=ALTIN + (a,))
    d.text((115, y), "KAYNAK", font=fb, fill=ALTIN + (a,))
    for s in sat:
        d.text((115, y + 36), s, font=f, fill=KREM + (int(a * 0.85),)); y += 36

def buyukler(L, d, sahne, t, koyu_metin=False):
    renk = MUREKKEP if koyu_metin else KREM
    for b in sahne.get("buyuk", []):
        a = fade(t, b["t"], 0.9)
        a = min(a, 1 - fade(t, sahne["son"] - 0.35, 0.35))
        if a <= 0: continue
        A = int(255 * a); st = b["stil"]; up = (1 - ease((t - b["t"]) / 1.2)) * 30
        if st == "dev":
            sz = int(150 + 14 * ease((t - b["t"]) / 4.4))
            f = font(LORA, sz, 600); ortala(d, 760 + up, b["metin"], f, KREM + (A,))
            lw = 260 * ease((t - b["t"] - 0.6) / 1.2)
            d.rectangle([W / 2 - lw / 2, 980, W / 2 + lw / 2, 984], fill=ALTIN + (A,))
        elif st == "arapca":
            ortala(d, 380 + up, b["metin"], font(ARAP_B, 230), renk + (A,), "rtl")
        elif st == "translit":
            ortala(d, 690 + up, b["metin"], font(LORA_I, 76, 500), (120, 72, 30, A))
        elif st == "kok_ar":
            ortala(d, 850 + up, b["metin"], font(ARAP_B, 150), (140, 40, 25, A), "rtl")
        elif st == "kok_tr":
            ortala(d, 1070 + up, b["metin"], font(INTER.format("SemiBold"), 44), renk + (A,))
        elif st == "alinti":
            f = font(LORA_I, 70, 500); y = 610 + up
            for s in b["metin"].split("\n"):
                ortala(d, y, s, f, (40, 26, 14, A)); y += 96
        elif st == "etiket":
            ortala(d, 560 + up, b["metin"], font(INTER.format("Bold"), 40), ALTIN + (A,))
        elif st == "isim":
            ortala(d, 630 + up, b["metin"], font(LORA, 104, 600), KREM + (A,))
        elif st == "alt_isim":
            ortala(d, 775 + up, b["metin"], font(LORA_I, 52, 400), KREM + (int(A * .85),))
        elif st == "uyari":
            f = font(INTER.format("Bold"), 28); s = b["metin"]; w = d.textlength(s, font=f)
            d.rounded_rectangle([(W - w) / 2 - 22, 880, (W + w) / 2 + 22, 932], 26, outline=ALTIN + (A,), width=2)
            ortala(d, 890, s, f, ALTIN + (A,))
        elif st == "final":
            f = font(LORA, 128, 600); y = 600 + up
            for s in b["metin"].split("\n"):
                ortala(d, y, s, f, (36, 22, 10, A)); y += 160

def zincir(d, sahne, t):
    y = 330
    for i, z in enumerate(sahne["zincir"]):
        a = fade(t, z["t"], 0.7); a = min(a, 1 - fade(t, sahne["son"] - 0.35, 0.35))
        if a <= 0: y += 250; continue
        A = int(255 * a); off = (1 - ease((t - z["t"]) / 0.9)) * 40
        d.ellipse([140 - 14, y + 30 - 14, 140 + 14, y + 30 + 14], fill=ALTIN + (A,))
        if i < len(sahne["zincir"]) - 1:
            ln = 250 * fade(t, z["t"] + 0.4, 0.8)
            d.rectangle([138, y + 48, 142, y + 48 + max(0, ln - 36)], fill=ALTIN + (int(A * .6),))
        d.text((190 + off, y), z["dil"], font=font(INTER.format("Bold"), 30), fill=ALTIN + (A,))
        d.text((190 + off, y + 44), z["kelime"], font=font(LORA_I if i == 0 else LORA, 80, 600), fill=KREM + (A,))
        if z["yazi"]:
            f = font(ARAP_B, 86); w = d.textlength(z["yazi"], font=f, direction="rtl")
            d.text((W - 110 - w, y + 30), z["yazi"], font=f, fill=KREM + (int(A * .8),), direction="rtl")
        y += 250

def kunye(L, d, sahne, t):
    a0 = fade(t, sahne["bas"], 0.6)
    A = int(255 * a0)
    ortala(d, 430, "KELİMELERİN", font(INTER.format("Bold"), 46), ALTIN + (A,))
    ortala(d, 495, "Gizli Tarihi", font(LORA, 120, 600), KREM + (A,))
    ortala(d, 660, "Her kelimenin bir hikâyesi var.", font(LORA_I, 46, 400), KREM + (int(A * .8),))
    a1 = int(255 * fade(t, sahne["bas"] + 0.9, 0.6))
    d.text((90, 860), "KAYNAKÇA", font=font(INTER.format("Bold"), 30), fill=ALTIN + (a1,))
    y = 912; f = font(INTER.format("Regular"), 28)
    for k in sahne["kaynakca"]:
        for s in satirla(d, "• " + k, f, 900):
            d.text((90, y), s, font=f, fill=KREM + (int(a1 * .85),)); y += 40
        y += 14
    a2 = fade(t, sahne["bas"] + 1.4, 0.7)
    if a2 > 0:
        lg = logo_img("beyaz", 380, a2); L.alpha_composite(lg, ((W - lg.width) // 2, 1330))
        ortala(d, 1330 + lg.height + 26, "havadis.at", font(INTER.format("SemiBold"), 34), KREM + (int(200 * a2),))

ZEMIN = {}
def zemin_kare(sahne, t):
    z = sahne["zemin"]; p = (t - sahne["bas"]) / (sahne["son"] - sahne["bas"])
    if z in ("kapi", "kapi_genis", "kapi_isik"):
        ac = {"kapi": 0.05 + 0.45 * ease(p * 1.1), "kapi_genis": 0.55 + 0.25 * ease(p),
              "kapi_isik": 0.85 + 0.6 * ease(p * 1.4)}[z]
        key = (z, round(ac, 2))
        if key not in ZEMIN:
            for k in [k for k in ZEMIN if isinstance(k, tuple)][:-3]: del ZEMIN[k]  # bellek sınırı
            ZEMIN[key] = z_kapi(min(ac, 1.4)).astype(np.uint8)
        return kenburns(ZEMIN[key], p, (1.0, 1.06), (0, -20))
    if z not in ZEMIN:
        ZEMIN[z] = {"gece": z_gece, "parsomen": z_parsomen, "col": z_col, "zincir": z_koyu, "kunye": z_koyu}[z]()
    zoom = {"gece": (1.0, 1.10), "parsomen": (1.02, 1.10), "col": (1.0, 1.07), "zincir": (1.0, 1.04), "kunye": (1.04, 1.0)}[z]
    return kenburns(ZEMIN[z], p, zoom, (0, -40))

def toz(d, t, n=70, renk=(255, 210, 150)):
    rng = random.Random(9)
    for i in range(n):
        x0, y0, sp = rng.random() * W, rng.random() * H, 8 + rng.random() * 25
        x = (x0 + math.sin(t * 0.4 + i) * 30) % W; y = (y0 - t * sp) % H
        r = 1 + rng.random() * 2.5; a = int(60 + 90 * (0.5 + 0.5 * math.sin(t * 1.3 + i)))
        d.ellipse([x - r, y - r, x + r, y + r], fill=renk + (a,))

LOGO = {k: Image.open(f"{__import__('os').path.dirname(__file__)}/../assets/logo-{k}.png").convert("RGBA") for k in ("beyaz", "siyah")}
def logo_img(renk, w, alpha=1.0):
    im = LOGO[renk]; h = int(im.height * w / im.width); im = im.resize((w, h), Image.LANCZOS)
    if alpha < 1: im.putalpha(im.split()[3].point(lambda v: int(v * alpha)))
    return im

def taslak_rozet(L, d, acik_zemin=False, logo=True):
    if logo: L.alpha_composite(logo_img("siyah" if acik_zemin else "beyaz", 190, 0.92), (64, 112))
    f = font(INTER.format("Bold"), 22); s = "TASLAK"
    w = d.textlength(s, font=f)
    d.rounded_rectangle([W - 64 - w - 32, 114, W - 64, 152], 19, fill=(0, 0, 0, 110))
    d.text((W - 64 - w - 16, 121), s, font=f, fill=(255, 255, 255, 200))

def kare(sen, t, gecis=0.45):
    sah = sen["sahneler"]
    cur = next(s for s in sah if s["bas"] <= t < s["son"] or s is sah[-1])
    bg = zemin_kare(cur, t)
    i = sah.index(cur)
    if i > 0 and t - cur["bas"] < gecis:  # çapraz geçiş
        onceki = sah[i - 1]
        bg = Image.blend(zemin_kare(onceki, onceki["son"] - 0.01), bg, ease((t - cur["bas"]) / gecis))
    if i == 0: bg = Image.blend(Image.new("RGB", (W, H)), bg, ease(t / 0.8))
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    if cur["zemin"] in ("gece", "col", "kapi", "kapi_genis"): toz(d, t)
    koyu = cur["zemin"] in ("parsomen",)
    buyukler(L, d, cur, t, koyu)
    if cur["zemin"] == "zincir": zincir(d, cur, t)
    if cur["zemin"] == "kunye": kunye(L, d, cur, t)
    # alt bant (okunabilirlik)
    if cur.get("altyazi") or cur.get("kaynak"):
        band = Image.new("RGBA", (W, H), (0, 0, 0, 0)); bd = ImageDraw.Draw(band)
        for k in range(H - 1180):
            bd.line([(0, 1180 + k), (W, 1180 + k)], fill=(8, 6, 4, int(185 * min(1, k / 260))))
        bg = Image.alpha_composite(bg.convert("RGBA"), band).convert("RGB")
    altyazi(d, cur, t); kaynak(d, cur, t); taslak_rozet(L, d, koyu, cur["zemin"] != "kunye")
    out = Image.alpha_composite(Image.alpha_composite(bg.convert("RGBA"), golge(L, 8, 120)), L).convert("RGB")
    arr = np.asarray(out, np.float32) + GRAIN[int(t * FPS) % 6]
    return np.clip(arr, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    sen = json.load(open(sys.argv[1])); muzik = sys.argv[2]; cikis = sys.argv[3]
    onizleme = sys.argv[4:] if len(sys.argv) > 4 else None
    if onizleme:
        for ts in onizleme:
            Image.fromarray(kare(sen, float(ts))).save(f"{cikis}_{ts}.jpg", quality=88)
        sys.exit()
    n = int(sen["sure"] * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", muzik,
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cikis],
                          stdin=subprocess.PIPE)
    for i in range(n):
        ff.stdin.write(kare(sen, i / FPS).tobytes())
        if i % 150 == 0: print(f"{i}/{n}", flush=True)
    ff.stdin.close(); ff.wait()
