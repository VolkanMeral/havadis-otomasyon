"""Wikimedia Commons'tan serbest lisanslı görselleri, lisans ve yazar bilgisiyle indirir.
Kullanım: python etimoloji/gorsel_indir.py etimoloji/<kelime>/gorsel.json
gorsel.json: {"aramalar": [{"id": "minyatur", "sorgu": "Ottoman miniature coffee", "adet": 4}]}"""
import json, os, re, sys, time, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "HavadisEtimolojiBot/1.0 (https://havadis.at; bot@havadis.at)"}
IZINLI = re.compile(r"(public domain|^pd|cc0|cc[ -]by(?!.*nc)(?!.*nd))", re.I)

def api(params):
    params.update({"format": "json", "formatversion": "2"})
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=60))

def temiz(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html or "")).strip()[:300]

def main(f):
    cfg = json.load(open(f)); out = os.path.join(os.path.dirname(f), "gorsel"); os.makedirs(out, exist_ok=True)
    meta_yol = os.path.join(out, "gorseller.json")
    meta = json.load(open(meta_yol)) if os.path.exists(meta_yol) else {}
    for a in cfg["aramalar"]:
        if any(k.startswith(a["id"] + "_") for k in meta): print(a["id"], "mevcut"); continue
        r = api({"action": "query", "generator": "search", "gsrsearch": a["sorgu"] + " filetype:bitmap", "gsrnamespace": 6,
                 "gsrlimit": 30, "prop": "imageinfo", "iiprop": "url|extmetadata|size|mime", "iiurlwidth": 1600})
        sayfalar = sorted(r.get("query", {}).get("pages", []), key=lambda p: p.get("index", 99))
        n = 0
        for p in sayfalar:
            ii = (p.get("imageinfo") or [{}])[0]; em = ii.get("extmetadata", {})
            lis = em.get("LicenseShortName", {}).get("value", "")
            if not IZINLI.search(lis) or ii.get("mime") not in ("image/jpeg", "image/png", "image/tiff"): continue
            if ii.get("width", 0) < 900: continue
            n += 1; ad = f"{a['id']}_{n}.jpg"
            try:
                req = urllib.request.Request(ii.get("thumburl") or ii["url"], headers=UA)
                open(os.path.join(out, ad), "wb").write(urllib.request.urlopen(req, timeout=120).read())
            except Exception as e:
                print("indirilemedi", p["title"], e); n -= 1; continue
            meta[ad] = {"baslik": p["title"], "sayfa": ii.get("descriptionurl"), "lisans": lis,
                        "yazar": temiz(em.get("Artist", {}).get("value")), "aciklama": temiz(em.get("ImageDescription", {}).get("value")),
                        "tarih": temiz(em.get("DateTimeOriginal", {}).get("value")), "sorgu": a["sorgu"]}
            print(ad, lis, p["title"], flush=True); time.sleep(1)
            if n >= a.get("adet", 4): break
        if n == 0: print(a["id"], "uygun görsel bulunamadı")
        json.dump(meta, open(meta_yol, "w"), ensure_ascii=False, indent=1)

if __name__ == "__main__":
    for f in sys.argv[1:]: main(f)
