"""Google Cloud Text-to-Speech (Chirp 3 HD) ile Türkçe ses örnekleri üretir. GOOGLE_TTS_KEY ortam değişkeni gerekir."""
import base64, json, os, sys, urllib.request
KEY = os.environ.get("GOOGLE_TTS_KEY")
if not KEY: print("GOOGLE_TTS_KEY yok, atlanıyor"); sys.exit(0)
metin = open("etimoloji/ses-deneme2/metin.txt", encoding="utf-8").read().strip()
out = "etimoloji/ses-deneme2/google"; os.makedirs(out, exist_ok=True)
sesler = ["Charon", "Fenrir", "Orus", "Algenib", "Alnilam", "Enceladus", "Puck", "Achird"]
for s in sesler:
    ad = f"tr-TR-Chirp3-HD-{s}"
    body = {"input": {"text": metin}, "voice": {"languageCode": "tr-TR", "name": ad},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.95}}
    req = urllib.request.Request(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={KEY}",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=60))
        open(f"{out}/{s}.mp3", "wb").write(base64.b64decode(r["audioContent"])); print(ad, "ok")
    except Exception as e:
        print(ad, "hata", getattr(e, "read", lambda: b"")()[:300])
