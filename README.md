# Havadis.at – Otomatik Instagram & Facebook paylaşımı

Bu sistem 08:00–22:30 arasında çalışır:
- **Saat başlarında** (08:00, 09:00 …): Avusturya, Vorarlberg, Avrupa, Almanya'dan en yeni haber **görsel** olarak.
- **Buçuklarda** (08:30, 09:30 …): sadece Vorarlberg'den en yeni haber görsel olarak.
- **15 geçe, günde 10 kez** (07, 08, 10, 11, 13, 14, 16, 17, 19, 20 saatlerinde): en yeni haber **12 sn'lik müzikli video (Reels)** olarak Instagram ve Facebook'a (0–5 sn manşet, 5–10 sn kısa haber, son 2 sn logo).
- **Pazar 11:05: haftalık özet videosu** ("Avusturya'da bu hafta"): son 7 günün 4–6 Avusturya/Vorarlberg haberi, seslendirme yok, özgün müzik + ekranda yazı, en fazla ~88 sn. Facebook Reels, Instagram Reels ve YouTube Shorts olarak paylaşılır (`haftalik_ozet.py`; elle deneme: `is=ozet`, `dry_run=1`).
- **Story:** Avusturya ve Vorarlberg haberleri paylaşıldıkları anda ayrıca Instagram ve Facebook Story'ye 12 saniyelik müzikli video olarak gider. (Story'ye tıklanabilir link etiketi otomatik eklenemez; Meta buna izin vermiyor.)

Yeni haber yoksa o çalışma hiçbir şey paylaşmadan birkaç saniyede biter.

Her çalışmada:

1. havadis.at RSS akışından henüz paylaşılmamış **en yeni haberi** seçer. Sadece Avusturya, Vorarlberg, Avrupa ve Almanya kategorileri paylaşılır.
2. Haberin fotoğrafını alır, Havadis şablonuyla **1080×1350 görsel** üretir. Varsayılan tasarım **tam ekran manşet**: fotoğraf bütün ekranı kaplar, başlık altta kırmızı vurgu bandıyla, köşede rakam etiketi. Küçük fotoğraflar yüksek kaliteyle büyütülüp keskinleştirilir.
3. Görseli **Facebook sayfasına** (habere tıklanabilir linkle) ve **Instagram hesabına** paylaşır.
4. Paylaşılan haberi `posted.json` dosyasına yazar, böylece aynı haber iki kez paylaşılmaz.

Ücretsiz bir GitHub hesabında, GitHub Actions ile çalışır. Sunucu gerekmez.

---

## Kurulum (bir kez, yaklaşık 30–45 dakika)

### 1. Instagram'ı Facebook sayfasına bağlayın
- Instagram uygulaması → Ayarlar → Hesap türü → **İşletme hesabı**na geçin.
- Facebook sayfası → Ayarlar → **Bağlı hesaplar** → Instagram'ı bağlayın.

### 2. Meta geliştirici uygulaması ve erişim anahtarı
1. https://developers.facebook.com → **Uygulama oluştur** → tür olarak **İşletme (Business)** seçin.
2. **Graph API Explorer**'ı açın (Araçlar menüsü). Sağdan uygulamanızı seçin, "User Token" alın ve şu izinleri işaretleyin:
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`, `business_management`
3. Aldığınız kısa süreli anahtarı **Access Token Debugger**'da açıp **"Extend Access Token"** ile uzun süreli hale getirin.
4. Graph API Explorer'da uzun süreli anahtarla şu sorguyu çalıştırın: `me/accounts`
   → Havadis sayfasının **`id`** değeri = `META_PAGE_ID`, **`access_token`** değeri = `META_PAGE_TOKEN` (bu sayfa anahtarının süresi dolmaz).
5. Şu sorguyu çalıştırın: `<META_PAGE_ID>?fields=instagram_business_account`
   → çıkan `id` = `IG_USER_ID`.

> Uygulamayı yalnızca kendi sayfanızda, uygulamada yönetici rolünüz varken kullandığınız için genellikle Meta'nın uygulama incelemesine gerek kalmaz. Daha sağlam bir yol isterseniz Meta Business Suite → İşletme Ayarları → **Sistem Kullanıcıları** üzerinden süresiz bir anahtar da oluşturabilirsiniz.

Bu anahtarları kimseyle paylaşmayın; sadece aşağıdaki GitHub "Secrets" alanına girin.

### 3. GitHub'a yükleyin
1. https://github.com üzerinde yeni bir **özel (private)** depo oluşturun, örn. `havadis-otomasyon`.
2. Bu klasördeki tüm dosyaları depoya yükleyin (`.github` klasörü dahil).
3. Depo → Settings → Secrets and variables → **Actions**:
   - **Secrets** sekmesine ekleyin: `META_PAGE_ID`, `META_PAGE_TOKEN`, `IG_USER_ID`
   - İsteğe bağlı TikTok: `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` (TikTok geliştirici uygulaması; yönlendirme adresi `https://havadis.at/`). Bağlamak için `python tiktok.py adres` ile çıkan adresi açıp izin verin, açılan havadis.at adresinin tamamını paylaşım görevini elle çalıştırırken `tiktok_kod` kutusuna yapıştırın. Şifreli yenileme anahtarı `tiktok_token.enc` olarak depoya kaydedilir (365 gün). Varsayılan mod **taslak** (`TIKTOK_MODE=inbox`): günde 5 video (TIKTOK_HOURS) TikTok taslaklarına gider, uygulamadan tek dokunuşla yayınlanır. TikTok incelemesi onaylanınca `TIKTOK_MODE=direct` ile doğrudan herkese açık paylaşılır.
   - İsteğe bağlı `THREADS_TOKEN`: Threads kullanıcı anahtarı (threads_basic + threads_content_publish, 60 gün geçerli). Tanımlıysa her haber Threads'e de başlık + kısa özet + tıklanabilir link önizlemesiyle gider; boşsa Threads atlanır. Süresi dolmadan yenilenmeli.
   - İsteğe bağlı: `ANTHROPIC_API_KEY` (aşağıya bakın)
   - **Variables** sekmesine ekleyin: `DRY_RUN` = `1` (önce deneme modu)

### 4. Deneme
- Depo → **Actions** → "Havadis saatlik paylaşım" → **Run workflow** (dry_run = 1).
- Çalışma bitince sayfanın altındaki **Artifacts** bölümünden üretilen görseli ve paylaşım metinlerini indirip kontrol edin.
- Her şey yolundaysa bir kez `dry_run = 0` ile elle çalıştırıp gerçek paylaşımı deneyin.
- Sonra **Variables** → `DRY_RUN` değerini `0` yapın. Sistem artık her saat kendiliğinden paylaşır.

---

## İsteğe bağlı: Yapay zekâ ile haber analizi
`ANTHROPIC_API_KEY` eklenirse her haber Claude ile analiz edilir ve şunlar yazılır:
kısa ve güçlü manşet (vurgulanacak kelimeler seçilerek), köşedeki rakam etiketi (örn. "+%35"),
görsel üzerindeki tek cümlelik özet, paylaşım metni ve habere özel hashtag'ler.
Anahtar yoksa sistem başlığı ":" işaretinden bölerek basit modda çalışır.
Anahtar: https://console.anthropic.com (kullanım başına küçük bir ücret alınır).

## Ayarlar
| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `DRY_RUN` | `1` | `1` = paylaşma, sadece görsel üret |
| `INCLUDE_CATEGORIES` | `Avusturya,Vorarlberg,Almanya,İsviçre,Sağlık,Dünya,Teknoloji,Havadis Özel,Avrupa` | Sadece bu kategoriler paylaşılır (virgülle; boş = hepsi) |
| `HALF_HOUR_CATEGORIES` | `Vorarlberg` | Buçuklardaki ek paylaşımlarda kullanılacak kategoriler |
| `SKIP_CATEGORIES` | `TAZİYE` | Paylaşılmayacak kategoriler (virgülle) |
| `MAX_AGE_HOURS` | `24` | Bundan eski haberler paylaşılmaz |
| `BASE_HASHTAGS` | `#havadis #Avusturya #haber` | Her paylaşıma eklenen hashtag'ler |
| `AI_LABEL` | `KI-unterstützt` | Görselin altında ve metnin sonunda küçük şeffaflık notu (AB Yapay Zekâ Yasası md. 50) |
| `VIDEO_HOURS` | `7,8,10,11,13,14,16,17,19,20` | 15 geçe video paylaşılacak saatler (Viyana saati) |
| `STORY_CATEGORIES` | `Avusturya,Vorarlberg` | Story'ye de giden kategoriler |
| `TEMPLATE` | `manset` | Tasarım: `manset` (tam ekran manşet) veya `kart` (sosyal gönderi kartı) |
| `GRAPH_VERSION` | `v26.0` | Meta Graph API sürümü |

Paylaşım saatlerini değiştirmek için `.github/workflows/paylas.yml` içindeki `cron` satırını düzenleyin (saatler UTC'dir).
Tasarımı değiştirmek için `sablon_manset.html` dosyasını düzenleyin. Sosyal gönderi kartı tasarımına geçmek için Variables bölümüne `TEMPLATE` = `kart` ekleyin.

## Bilinmesi gerekenler
- GitHub zamanlanmış görevleri yoğun saatlerde birkaç dakika gecikebilir.
- Kış saatine geçişte paylaşım saatleri bir saat kayar (07:00–21:00). İsterseniz `cron` satırını `0 7-21 * * *` yapın.
- Instagram API ile 24 saatte en az 50 paylaşım yapılabilir; bu sistem günde en fazla 30 paylaşım yapar (yeni haber yoksa daha az).
- Özel depolarda GitHub Actions ayda 2.000 dakika ücretsizdir. Yeni haber olmayan çalışmalar ağır kurulumu atladığı için kısa sürer; kullanımı Settings → Billing bölümünden takip edebilirsiniz.
- Instagram açıklamalarında linkler tıklanmaz; bu yüzden metinde "profildeki link" yönlendirmesi var. Facebook'ta haber linki doğrudan eklenir.
- Ajans fotoğraflarının sosyal medyada kullanım hakkı ayrı olabilir; sitede kullandığınız fotoğrafların sosyal medya hakkını kontrol edin.


## YouTube Shorts (isteğe bağlı)
15 geçe paylaşılan haber videoları, aşağıdaki üç secret tanımlıysa YouTube kanalına Shorts olarak da yüklenir
(başlık, kısa açıklama, haber linki; kategori "Haberler ve Politika"). Tanımlı değilse bu adım atlanır.
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`: Google Cloud → API'ler ve Hizmetler → Kimlik bilgileri → OAuth istemci kimliği (Web uygulaması)
- `YOUTUBE_REFRESH_TOKEN`: Google OAuth Playground ile kanal hesabından alınır (kapsam: `https://www.googleapis.com/auth/youtube`)
OAuth onay ekranı **In production** durumunda olmalı; "Testing" durumunda yenileme anahtarı 7 günde geçersiz olur.
Kontrol: Actions → elle çalıştır → `sadece_kontrol` = 1 (kanal adını yazar, paylaşım yapmaz).
