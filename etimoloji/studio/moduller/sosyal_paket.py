"""Bölüm için sosyal medya metinleri üretir: bolumler/<k>/sosyal_paket.md"""
import json, sys, runpy
KANCA = {"merhaba": "Her gün söylüyoruz ama aslında bir yer tarif ediyoruz.",
         "kahve": "Sabah içtiğiniz kahvenin adı bir zamanlar 'şarap' demekti.",
         "yogurt": "Dünyanın pek çok dilinde aynı Türkçe kelime: yoğurt.",
         "kosk": "Gazete aldığınız kiosk, bir zamanlar 'saray' demekti.",
         "lale": "Avrupa laleye yüzyıllardır bir sarığın adıyla sesleniyor.",
         "divan": "Salondaki sedirle sınırdaki gümrük aynı kelimeden geliyor."}
def paket(k):
    s = json.load(open(f"bolumler/{k}/senaryo.json")); kun = [x for x in s["sahneler"] if x["id"] == "kunye"][0]
    kredi = sorted({x["kredi"] for x in s["sahneler"] if x.get("kredi")})
    b = s.get("bolum", 1); kel = s["kelime"].title()
    kaynak = "\n".join("• " + x for x in kun["kaynakca"]); gorsel = "\n".join("• " + x for x in kredi)
    tag = f"#{kel.replace('Â','A').replace('İ','I').replace('Ö','O').replace('Ğ','G').replace('Ş','S')} #KelimelerinGizliTarihi #Etimoloji #Türkçe #Dil #Tarih #Havadis"
    md = f"""# {s['kelime']} – Sosyal medya paketi (Bölüm {b})

## Instagram / Facebook Reels
**Başlık:** {kel}: Kelimelerin Gizli Tarihi #{b}

{KANCA[k]} 👇
Kelimelerin Gizli Tarihi'nin {b}. bölümünde "{kel.lower()}" kelimesinin yolculuğu.

📚 Kaynaklar:
{kaynak}

🖼 Görseller (temsilî): Wikimedia Commons, serbest lisans – ayrıntılar sabit yorumda.
🤖 KI-unterstützt · Seslendirme yapay zekâ sesidir.

{tag}

## TikTok
{KANCA[k]} Kelimelerin Gizli Tarihi #{b} 📜 Kaynaklar açıklamada ve sabit yorumda. 🤖 KI-unterstützt
{tag} #fyp

## YouTube Shorts
**Başlık:** {kel} kelimesinin gizli tarihi #{b} #Shorts
**Açıklama:**
{KANCA[k]}
Kaynaklar:
{kaynak}
Görseller (temsilî, Wikimedia Commons):
{gorsel}
🤖 KI-unterstützt.

## Sabit yorum
📚 Kaynakça ve görsel lisansları:
{kaynak}
{gorsel}
Bir hata gördüyseniz yazın; düzeltip açıklamaya ekliyoruz.
"""
    open(f"bolumler/{k}/sosyal_paket.md", "w").write(md); print("paket:", k)
for k in sys.argv[1:]: paket(k)
