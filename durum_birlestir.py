"""Durum dosyalarini (posted.json, arsiv.json, karusel_durum.json) birlestirir.

Iki calisma ayni anda durum kaydettiginde git rebase JSON'da cakisma verir.
Bu betik, bu calismanin yerel kopyasini (yedek klasoru) depodaki guncel
surumle (calisma dizini) kayit kaybetmeden birlestirir.

Kullanim: python durum_birlestir.py <yedek_klasoru>
"""
import json
import os
import sys


def oku(yol, varsayilan):
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return varsayilan


def yaz(yol, veri):
    with open(yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=1)


def link_birlestir(uzak, yerel, siralama_anahtari, sinir=None):
    kayit = {}
    for h in uzak + yerel:  # ayni link: yerel (yeni) surum kazanir, alanlar birlesir
        if isinstance(h, dict) and h.get("link"):
            kayit[h["link"]] = {**kayit.get(h["link"], {}), **h}
    sonuc = sorted(kayit.values(), key=lambda h: h.get(siralama_anahtari) or "")
    return sonuc[-sinir:] if sinir else sonuc


def main(yedek):
    if os.path.exists(os.path.join(yedek, "posted.json")):
        yaz("posted.json", link_birlestir(
            oku("posted.json", []), oku(os.path.join(yedek, "posted.json"), []), "zaman", 500))
    if os.path.exists(os.path.join(yedek, "arsiv.json")):
        yaz("arsiv.json", link_birlestir(
            oku("arsiv.json", []), oku(os.path.join(yedek, "arsiv.json"), []), "tarih"))
    if os.path.exists(os.path.join(yedek, "karusel_durum.json")):
        uzak = oku("karusel_durum.json", {})
        yerel = oku(os.path.join(yedek, "karusel_durum.json"), {})
        yaz("karusel_durum.json", {**uzak, **yerel})


if __name__ == "__main__":
    main(sys.argv[1])
