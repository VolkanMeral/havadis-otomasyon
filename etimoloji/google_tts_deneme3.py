"""Kalın ve doğal anlatıcı denemesi: Chirp 3 HD erkek sesleri, yavaş tempo. GOOGLE_TTS_KEY gerekir."""
import base64, json, os, sys, urllib.request
KEY = os.environ.get("GOOGLE_TTS_KEY")
if not KEY: print("GOOGLE_TTS_KEY yok"); sys.exit(0)
metin = open("etimoloji/ses-deneme3/metin.txt", encoding="utf-8").read().strip()
out = "etimoloji/ses-deneme3/google"; os.makedirs(out, exist_ok=True)
for s, hiz in [("Charon", 0.9), ("Fenrir", 0.9), ("Orus", 0.9), ("Alnilam", 0.9), ("Algenib", 0.9), ("Iapetus", 0.9), ("Rasalgethi", 0.9), ("Puck", 0.9)]:
    body = {"input": {"text": metin}, "voice": {"languageCode": "tr-TR", "name": f"tr-TR-Chirp3-HD-{s}"},
            "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": 44100, "speakingRate": hiz}}
    req = urllib.request.Request(f"https://texttospeech.googleapis.com/v1/text:synthesize?key={KEY}",
                                 data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=60))
        open(f"{out}/{s}.wav", "wb").write(base64.b64decode(r["audioContent"])); print(s, "ok")
    except Exception as e:
        print(s, "hata", getattr(e, "read", lambda: b"")()[:300])
