"""Etimoloji anlatım parçalarını edge-tts ile üretir.
dil alanı verilirse (ör. tr-TR) çok dilli seslere metnin dili <lang> etiketiyle bildirilir,
böylece ş, ç, ğ, ı gibi sesler o dilin kurallarıyla okunur. Etiket reddedilirse düz moda düşer."""
import asyncio, json, os, sys, time
import edge_tts
from edge_tts import communicate as C

DIL = None
_orj = C.mkssml
def _mkssml(*a, **k):
    s = _orj(*a, **k)
    if DIL:
        s = s.replace("<prosody", f"<lang xml:lang='{DIL}'><prosody", 1).replace("</prosody>", "</prosody></lang>", 1)
    return s
C.mkssml = _mkssml

async def uret(metin, ses, hiz, perde, yol):
    await edge_tts.Communicate(metin, ses, rate=hiz, pitch=perde).save(yol)

def main(f):
    global DIL
    d = json.load(open(f)); out = os.path.join(os.path.dirname(f), "ses"); os.makedirs(out, exist_ok=True)
    rapor = {}; hatali = []
    for p in d["parcalar"]:
        yol = f"{out}/{p['id']}.mp3"
        if os.path.exists(yol) and os.path.getsize(yol) > 4000: rapor[p["id"]] = "mevcut"; continue
        ok = False
        for mod in ([d["dil"], None] if d.get("dil") else [None]):
            DIL = mod
            for deneme in range(3):
                try:
                    asyncio.run(uret(p.get("ses_metni", p["metin"]), d["ses"], d["hiz"], d["perde"], yol))
                    ok = os.path.getsize(yol) > 4000
                except Exception as e:
                    print(p["id"], mod, "hata:", type(e).__name__, str(e)[:200], flush=True); ok = False
                if ok: break
                time.sleep(2 + deneme * 2)
            if ok: rapor[p["id"]] = f"lang={mod}" if mod else "duz"; break
        print(p["id"], rapor.get(p["id"], "HATA"), flush=True)
        if not ok: hatali.append(p["id"])
        time.sleep(1)
    json.dump(rapor, open(f"{out}/rapor.json", "w"), indent=1)
    if hatali: sys.exit("eksik: " + ",".join(hatali))

if __name__ == "__main__":
    for f in sys.argv[1:]: main(f)
