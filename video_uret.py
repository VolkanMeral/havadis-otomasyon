#!/usr/bin/env python3
"""Haber videosu üretir: paylaşılan grafikle aynı tasarım, tam dikey ekran (1080x1920, 9:16) olarak.
Öğeler sırayla belirir; yazılar Instagram/Facebook Reels düğmelerinin üstünde kalır."""
import os
import subprocess

import havadis_bot as bot

FPS = 30
W, H = 1080, 1920
SURE = float(os.getenv("VIDEO_SECONDS", "12"))
MUZIK = os.getenv("VIDEO_MUSIC", os.path.join(bot.KOK, "assets", "muzik.wav"))  # boş bırakılırsa sessiz

# Grafik şablonunun üzerine eklenen animasyon: t saniyesindeki görünümü çizer
ANIMASYON = """
<style>
  /* Grafik tasarımını dikey ekrana uyarla: fotoğraf üstte tam genişlikte, yazılar Reels arayüzünün üstünde */
  body, .kart { height: 1920px !important; }
  .foto { inset: 0 0 auto 0 !important; height: 1640px !important; }
  .alt-golge { height: 1250px !important;
               background: linear-gradient(#070B1400 0%, #070B14d9 34%, #070B14 60%) !important; }
  .ust-golge { height: 520px !important; }
  .ust { top: 230px !important; }  /* Story/Reels üst arayüzünün (ilerleme çubuğu, profil adı) altında */
  .alt { bottom: 270px !important; }  /* Reels açıklama satırının üstünde */
  h1 .vurgu { position: relative; }
  .perde { position: absolute; inset: 0; background: #070B14; pointer-events: none; }
  /* Son 2 saniye: logolu kapanış */
  .kapanis { position: absolute; inset: 0; background: #070B14; display: flex; align-items: center;
             justify-content: center; opacity: 0; z-index: 10; }
  .kapanis img { width: 620px; height: auto; display: block; }
  /* İkinci sayfa: haberin kısa içeriği */
  .sayfa2 { position: absolute; left: 64px; right: 64px; bottom: 410px; display: flex; flex-direction: column;
            gap: 34px; opacity: 0; z-index: 4; }
  .sayfa2 .ust2 { display: flex; gap: 14px; align-items: center; }
  .sayfa2 .k { background: #E42320; font-family: 'Barlow Condensed', sans-serif; font-size: 30px; font-weight: 800;
               letter-spacing: 3px; padding: 8px 18px; text-transform: uppercase; }
  .sayfa2 .kisaca { font-family: 'Barlow Condensed', sans-serif; font-size: 30px; font-weight: 700;
                    letter-spacing: 4px; color: rgba(255,255,255,.85); text-transform: uppercase; }
  .sayfa2 .metin2 { border-left: 8px solid #E42320; padding-left: 34px; display: flex; flex-direction: column; gap: 26px; }
  .sayfa2 .metin2 p { margin: 0; font-family: 'Barlow', sans-serif; font-weight: 600; font-size: 54px;
                      line-height: 1.28; color: #fff; }
  /* Sesli videoda altyazı: fotoğrafın üzerinde, ortada */
  .altyazi { position: absolute; left: 80px; right: 80px; top: 430px; display: flex; justify-content: center;
             z-index: 5; pointer-events: none; }
  .altyazi span { background: rgba(7,11,20,.82); color: #fff; font-family: 'Barlow', Arial, sans-serif;
                  font-weight: 700; font-size: 50px; line-height: 1.25; padding: 12px 22px; border-radius: 12px;
                  text-align: center; -webkit-box-decoration-break: clone; box-decoration-break: clone; }
</style>
<script>
  (function () {
    const SURE = __SURE__;
    const q = s => document.querySelector(s);
    const ilerle = (t, a, b) => Math.min(1, Math.max(0, (t - a) / (b - a)));
    const yumusak = x => 1 - Math.pow(1 - x, 3);
    const perde = document.createElement('div'); perde.className = 'perde';
    q('.foto').after(perde);
    const kapanis = document.createElement('div'); kapanis.className = 'kapanis';
    const logo = document.createElement('img'); logo.src = q('.ust img').src; logo.alt = 'Havadis.at';
    kapanis.appendChild(logo); q('.kart').appendChild(kapanis);
    const OZET2 = __OZET2__, GECIS = __GECIS__;
    const s2 = document.createElement('div'); s2.className = 'sayfa2';
    s2.innerHTML = '<div class="ust2"><div class="k"></div><div class="kisaca">Kısaca</div></div><div class="metin2"></div>';
    s2.querySelector('.k').textContent = q('.kategori .k').textContent;
    const cumleler = OZET2.split(/(?<=[.!?…]["”’]?)\\s+/).map(c => c.trim()).filter(Boolean);  // "2.400" bölünmez
    const pler = cumleler.map(c => { const p = document.createElement('p'); p.textContent = c; s2.querySelector('.metin2').appendChild(p); return p; });
    q('.kart').appendChild(s2);
    // Uzun metin üstteki logoya taşmasın
    s2.style.opacity = 0;
    let px = 54;
    while (s2.getBoundingClientRect().top < 420 && px > 36) { px -= 2; pler.forEach(p => p.style.fontSize = px + 'px'); }
    const ALTYAZI = __ALTYAZI__;
    const altyazi = document.createElement('div'); altyazi.className = 'altyazi';
    const altyaziMetin = document.createElement('span'); altyazi.appendChild(altyaziMetin);
    q('.kart').appendChild(altyazi);
    function goster(el, d, dx, dy) {
      if (!el) return;
      el.style.opacity = d;
      el.style.transform = `translate(${dx * (1 - d)}px, ${dy * (1 - d)}px)`;
    }
    window.kare = function (t) {
      q('.foto').style.transform = `scale(${1 + 0.08 * t / SURE})`;
      perde.style.opacity = 0.45 * (1 - yumusak(ilerle(t, 0, 0.9)));
      goster(q('.ust'), yumusak(ilerle(t, 0.2, 0.8)), 0, -20);
      // 1. sayfa çıkışı / 2. sayfa girişi
      const cik = yumusak(ilerle(t, GECIS - 0.35, GECIS + 0.15)), gir = yumusak(ilerle(t, GECIS, GECIS + 0.6));
      goster(q('.kategori'), yumusak(ilerle(t, 0.7, 1.2)) * (1 - cik), -60, 0);
      goster(q('h1 .beyaz'), yumusak(ilerle(t, 1.1, 1.7)) * (1 - cik), 0, 40);
      const v = yumusak(ilerle(t, 1.7, 2.4)) * (1 - cik);
      const vurgu = q('h1 .vurgu'); vurgu.style.opacity = v; vurgu.style.left = `${-80 * (1 - v)}px`;
      goster(q('.ozet'), yumusak(ilerle(t, 2.6, 3.2)) * (1 - cik), 0, 30);
      q('.alt').style.transform = `translateY(${-60 * cik}px)`;
      s2.style.opacity = gir;
      s2.style.transform = `translateY(${50 * (1 - gir)}px)`;
      pler.forEach((p, i) => goster(p, yumusak(ilerle(t, GECIS + 0.3 + i * 0.9, GECIS + 0.9 + i * 0.9)), 0, 24));
      q('.foto').style.filter = `blur(${10 * gir}px) brightness(${1 - 0.45 * gir})`;
      const ac = yumusak(ilerle(t, 3.0, 3.6));  // alt satır 2. sayfada yerinde kalır
      q('.alt-cizgi').style.opacity = ac;
      q('.alt-cizgi').style.transform = `translateY(${20 * (1 - ac) + 60 * cik}px)`;
      const k = yumusak(ilerle(t, SURE - 2.0, SURE - 1.5));
      kapanis.style.opacity = k;
      const parca = ALTYAZI.find(a => t >= a[0] && t < a[1]);
      altyazi.style.display = parca && k < 0.5 ? 'flex' : 'none';
      if (parca && altyaziMetin.textContent !== parca[2]) altyaziMetin.textContent = parca[2];
      logo.style.transform = `scale(${0.9 + 0.1 * yumusak(ilerle(t, SURE - 2.0, SURE - 1.0))})`;
    };
  })();
</script>
"""


def video_uret(h, ic, cikti_yolu, foto_bayt=None, ses=None, altyazi=None, sure=None):
    """ses: seslendirme dosyası (wav/mp3) – verilirse video sesli olur.
    altyazi: [(başlangıç sn, bitiş sn, metin), ...] – verilirse ekranda altyazı gösterilir.
    sure: video süresi (sn); verilmezse VIDEO_SECONDS.
    Akış (12 sn): 0-5 sn manşet sayfası, 5-10 sn haberin kısa içeriği, son 2 sn Havadis logosu.
    Seslendirme verilmezse assets/muzik.wav arka plan müziği kullanılır (VIDEO_MUSIC="" → sessiz)."""
    import json
    if bot.SABLON != "manset":
        raise RuntimeError("Video şu an sadece tam ekran manşet tasarımıyla çalışır (TEMPLATE=manset).")
    sure = float(sure or SURE)
    sayfa = bot.sayfa_hazirla(h, ic, foto_bayt)
    ozet2 = bot.kisalt(h.get("ozet") or ic.get("ozet") or "", 420)
    gecis = round(sure * 5 / 12, 2)  # 12 sn'lik videoda 5. saniye
    anim = (ANIMASYON.replace("__SURE__", str(sure)).replace("__GECIS__", str(gecis))
            .replace("__OZET2__", json.dumps(ozet2, ensure_ascii=False))
            .replace("__ALTYAZI__", json.dumps(altyazi or [], ensure_ascii=False)))
    if not ses and MUZIK and os.path.exists(MUZIK):
        ses = MUZIK
    sayfa = sayfa.replace("</body>", anim + "</body>")

    toplam = int(sure * FPS)
    ses_girdisi = ["-i", ses] if ses else ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]
    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         *ses_girdisi, "-af", "apad", "-t", str(sure), "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", cikti_yolu],
        stdin=subprocess.PIPE)

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        tarayici = p.chromium.launch()
        s = tarayici.new_page(viewport={"width": W, "height": H})
        s.set_content(sayfa, wait_until="networkidle", timeout=60000)
        s.evaluate("document.fonts.ready")
        s.evaluate("() => { if (window.sigdir) window.sigdir(); }")
        for i in range(toplam):
            s.evaluate(f"() => window.kare({i / FPS})")
            ffmpeg.stdin.write(s.screenshot(type="jpeg", quality=92))
        tarayici.close()
    ffmpeg.stdin.close()
    if ffmpeg.wait() != 0:
        raise RuntimeError("ffmpeg video oluşturamadı")
    return cikti_yolu


KAPAK_SANIYE = 4.5  # bu anda tüm yazılar ekranda: Reels kapağı olarak kullanılır


def kapak_uret(video_yolu, cikti_yolu):
    """Videonun kapak karesini JPEG olarak çıkarır."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(KAPAK_SANIYE), "-i", video_yolu,
                    "-frames:v", "1", "-q:v", "2", cikti_yolu], check=True)
    return cikti_yolu
