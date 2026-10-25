"""Kısa bölüm tanımından senaryo.json, anlatim.json ve gorsel.json üretir.
Kullanım: python bolum_olustur.py bolumler.py   (her bölüm bolumler/<kelime>/ altına yazılır)"""
import json, os, sys, runpy

def olustur(b, kok_dizin):
    d = os.path.join(kok_dizin, b["klasor"]); os.makedirs(d, exist_ok=True)
    S = []
    def sahne(id_, zemin, buyuk=(), kaynak=None, **ek):
        s = {"id": id_, "bas": 0, "son": 1, "zemin": zemin, "buyuk": list(buyuk), "altyazi": []}
        if kaynak: s["kaynak"] = kaynak
        s.update(ek); S.append(s)
    sahne("giris", "gece", [{"metin": b["kelime"], "t": 0.0, "stil": "acilis"}], arapca=b.get("yazi", ""))
    sahne("gizem", "kapi")
    k = b["kok"]
    by = []
    if k.get("yazi"): by.append({"metin": k["yazi"], "t": 0.15, "stil": "arapca"})
    by.append({"metin": k["translit"], "t": 0.3, "stil": "translit"})
    by.append({"metin": k["cip"], "t": 0.6, "stil": "kok_tr"})
    if k.get("uyari"): by.append({"metin": k["uyari"], "t": 0.75, "stil": "uyari_alt"})
    sahne("kok", "parsomen", by, k["kaynak"])
    a = b["anlam"]
    sahne("anlam", "kapi_genis", [{"metin": a["alinti"], "t": 0.1, "stil": "alinti", "etiket": a["etiket"]}], a["kaynak"])
    o = b["olay"]
    oy = [{"metin": o["etiket"], "t": 0.05, "stil": "etiket"}, {"metin": o["isim"], "t": 0.12, "stil": "isim"},
          {"metin": o["alt"], "t": 0.2, "stil": "alt_isim"}]
    if o.get("uyari"): oy.append({"metin": o["uyari"], "t": 0.55, "stil": "uyari"})
    sahne("rivayet", "col", oy, o["kaynak"])
    sahne("yolculuk", "zincir", kaynak=b["yolculuk"]["kaynak"],
          zincir=[{"dil": z[0], "kelime": z[1], "yazi": z[2] if len(z) > 2 else "", "t": 0.08 + i * 0.17} for i, z in enumerate(b["yolculuk"]["zincir"])])
    sahne("kapanis", "kapi_isik", [{"metin": b["final"], "t": 0.6, "stil": "final"}])
    sahne("kunye", "kunye", kaynakca=b["kaynakca"])
    # göreli zamanları (0..1) sahne süresi 10 sn varsayımıyla mutlak yap; zamanla.py yeniden ölçekler
    t = 0
    for s in S:
        s["bas"], s["son"] = t, t + 10
        for x in s.get("buyuk", []): x["t"] = t + x["t"] * 10
        for x in s.get("zincir", []): x["t"] = t + x["t"] * 10
        t += 10
    for s in S:
        if s["id"] in b.get("gorseller", {}):
            s["gorsel"], s["kredi"] = b["gorseller"][s["id"]]
    sen = {"kelime": b["kelime"], "bolum": b["bolum"], "seri": "Kelimelerin Gizli Tarihi",
           "slogan": "Her kelimenin bir hikâyesi var.", "sure": t, "sahneler": S}
    json.dump(sen, open(os.path.join(d, "senaryo.json"), "w"), ensure_ascii=False, indent=1)
    parc = []
    for sid, cumleler in b["anlatim"].items():
        for i, c in enumerate(cumleler, 1):
            kisa = {"giris": "g", "gizem": "z", "kok": "k", "anlam": "a", "rivayet": "r", "yolculuk": "y", "kapanis": "s", "kunye": "n"}[sid]
            p = {"id": f"{kisa}{i}", "sahne": sid, "metin": c if isinstance(c, str) else c[0]}
            if not isinstance(c, str):
                if len(c) > 1 and c[1]: p["ekran"] = c[1]
            parc.append(p)
    an = {"ses": "tr-TR-AhmetNeural", "hiz": "-2%", "perde": "-6Hz", "parcalar": parc}
    json.dump(an, open(os.path.join(d, "anlatim.json"), "w"), ensure_ascii=False, indent=1)
    json.dump({"aramalar": b["gorsel_ara"]}, open(os.path.join(d, "gorsel.json"), "w"), ensure_ascii=False, indent=1)
    print("hazır:", d, len(parc), "cümle")

if __name__ == "__main__":
    ns = runpy.run_path(sys.argv[1]); hedef = sys.argv[2] if len(sys.argv) > 2 else "bolumler"
    for b in ns["BOLUMLER"]: olustur(b, hedef)
