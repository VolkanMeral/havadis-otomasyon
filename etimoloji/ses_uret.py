"""Etimoloji anlatım parçalarını edge-tts ile üretir.
dil alanı verilirse (ör. tr-TR) çok dilli seslere metnin dili SSML xml:lang ile bildirilir,
böylece ş, ç, ğ, ı gibi sesler o dilin kurallarıyla okunur. Etiket reddedilirse düz moda düşer."""
import asyncio, json, os, sys, time
import edge_tts
from edge_tts import communicate as C

DIL = None
_orj = C.mkssml
def _mkssml(*a, **k):
    s = _orj(*a, **k)
    if DIL:
        import re
        s = re.sub(r"xml:lang='[^']*'", f"xml:lang='{DIL}'", s, count=1)
    return s
C.mkssml = _mkssml

def tts_temizle(metin):
    """Kesme işaretli ekleri (Sarayı'nda, Bağdat'ın) birleştirir; aksi hâlde ses ekleri harf harf okuyor."""
    import re
    metin = re.sub(r"(\w)['’‘](\w)", r"\1\2", metin)
    return metin.replace("“", "").replace("”", "").replace("„", "")

def google_uret(metin, ses, hiz, yol):
    import base64, urllib.request
    key = os.environ["GOOGLE_TTS_KEY"]
    body = {"input": {"text": tts_temizle(metin)}, "voice": {"languageCode": "tr-TR", "name": ses},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": float(hiz), "sampleRateHertz": 44100}}
    req = urllib.request.Request(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=60))
    open(yol, "wb").write(base64.b64decode(r["audioContent"]))

async def uret(metin, ses, hiz, perde, yol):
    await edge_tts.Communicate(metin, ses, rate=hiz, pitch=perde).save(yol)

def main(f):
    global DIL
    d = json.load(open(f)); out = os.path.join(os.path.dirname(f), "ses"); os.makedirs(out, exist_ok=True)
    rapor = {}; hatali = []
    for p in d["parcalar"]:
        yol = f"{out}/{p['id']}.mp3"
        if os.path.exists(yol) and os.path.getsize(yol) > 2000: rapor[p["id"]] = "mevcut"; continue
        ok = False
        if d.get("motor") == "google":
            for deneme in range(4):
                try:
                    google_uret(p.get("ses_metni", p["metin"]), d["ses"], d.get("hiz", 0.95), yol); ok = os.path.getsize(yol) > 2000
                except Exception as e:
                    print(p["id"], "google hata:", str(e)[:200], flush=True)
                if ok: break
                time.sleep(3)
            rapor[p["id"]] = "google" if ok else "HATA"
            print(p["id"], rapor[p["id"]], flush=True)
            if not ok: hatali.append(p["id"])
            continue
        for mod in ([d["dil"], None] if d.get("dil") else [None]):
            DIL = mod
            ham = p.get("ses_metni", p["metin"])
            varyant = [ham, ham.rstrip(",.:;!? ") + ".", ham.replace(",", ""), ham.replace("'", "").replace("’", ""), "Evet. " + ham]
            ayarlar = [(d["hiz"], d["perde"]), ("+0%", d["perde"]), (d["hiz"], "-5Hz")]
            denemeler = [(v, h, pr) for v in varyant for (h, pr) in ayarlar][:6]
            for deneme, (metin, hiz, perde) in enumerate(denemeler):
                try:
                    asyncio.run(uret(metin, d["ses"], hiz, perde, yol))
                    ok = os.path.getsize(yol) > 4000
                except Exception as e:
                    print(p["id"], mod, "hata:", type(e).__name__, str(e)[:120], flush=True); ok = False
                if ok:
                    if metin.startswith("Evet. "): rapor.setdefault("_kirp", []).append(p["id"])
                    break
                time.sleep(3 + (deneme % 3) * 2)
            if ok: rapor[p["id"]] = (f"lang={mod}" if mod else "duz") + f" {hiz} {perde}"; break
        print(p["id"], rapor.get(p["id"], "HATA"), flush=True)
        if not ok: hatali.append(p["id"])
        time.sleep(2.5)
    json.dump(rapor, open(f"{out}/rapor.json", "w"), indent=1)
    if hatali: sys.exit("eksik: " + ",".join(hatali))

if __name__ == "__main__":
    import traceback
    hata = []
    for f in sys.argv[1:]:
        try: main(f)
        except BaseException as e:
            hata.append(f); open(os.path.join(os.path.dirname(f), "ses_gunluk.txt"), "a").write(f"{f}\n{traceback.format_exc()[-2500:]}\n")
    if hata: sys.exit("hatalı: " + ", ".join(hata))
