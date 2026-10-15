# Havadis.at – Otomatik Instagram & Facebook paylaşımı

Bu sistem 08:00–22:30 arasında çalışır:
- **Saat başlarında** (08:00, 09:00 …): Avusturya, Vorarlberg, Avrupa, Almanya'dan en yeni haber **görsel** olarak.
- **Buçuklarda** (08:30, 09:30 …): sadece Vorarlberg'den en yeni haber görsel olarak.
- **15 geçe, günde 5 kez** (08:15, 11:15, 14:15, 17:15, 20:15): en yeni haber **video (Reels)** olarak Instagram ve Facebook'a.
- **Story:** Avusturya ve Vorarlberg haberleri paylaşıldıkları anda ayrıca Instagram Story'ye 10 saniyelik video olarak gider. (Story'ye tıklanabilir link etiketi otomatik eklenemez; Meta buna izin vermiyor.)

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
| `INCLUDE_CATEGORIES` | `Avusturya,Vorarlberg,Avrupa,Almanya` | Sadece bu kategoriler paylaşılır (virgülle; boş = hepsi) |
| `HALF_HOUR_CATEGORIES` | `Vorarlberg` | Buçuklardaki ek paylaşımlarda kullanılacak kategoriler |
| `SKIP_CATEGORIES` | `TAZİYE` | Paylaşılmayacak kategoriler (virgülle) |
| `MAX_AGE_HOURS` | `24` | Bundan eski haberler paylaşılmaz |
| `BASE_HASHTAGS` | `#havadis #Avusturya #haber` | Her paylaşıma eklenen hashtag'ler |
| `AI_LABEL` | `KI-unterstützt` | Görselin altında ve metnin sonunda küçük şeffaflık notu (AB Yapay Zekâ Yasası md. 50) |
| `VIDEO_HOURS` | `8,11,14,17,20` | 15 geçe video paylaşılacak saatler (Viyana saati) |
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
