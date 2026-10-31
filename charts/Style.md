# Dashboard Hub – Renk ve Tasarım Sistemi

Bu doküman, G01–G11 arasındaki tüm modüllerde kullanılan ortak görsel dili tanımlar.
Yeni bir modül eklerken bu değerler korunmalıdır.

## 1. Tasarım Değişkenleri (CSS `:root`)

| Değişken | Renk | Kullanım |
|---|---|---|
| `--background` | `#F3F4F6` | Genel sayfa arka planı |
| `--panel` | `#FFFFFF` | Kart, panel ve grafik alanı arka planı |
| `--text` | `#1F2937` | Ana metin |
| `--muted` | `#6B7280` | İkincil metin, açıklamalar, etiketler |
| `--border` | `#E5E7EB` | Kart ve panel kenarlıkları |
| `--accent` | `#7B1113` | Ana vurgu (bağlantılar, odak) |
| `--accent-hover` | `#5F0D0F` | Vurgu hover durumu |

Ek grafik renkleri (Plotly tarafında kullanılır):

| Renk | Kullanım |
|---|---|
| `#D1D5DB` | Eksen çizgisi, kenarlık (grafik içi) |
| `#9CA3AF` | İnce yardımcı çizgiler, güven aralığı sınırları |
| `#E5E7EB` | Izgara (grid) çizgileri |

## 2. Tipografi

- Yazı tipi: **Inter** (Google Fonts), ağırlıklar 400 / 600 / 700.
- Plotly grafik içi yazı tipi: Arial, sans-serif (mevcut modüllerde böyle).
- Sayfa başlığı (H1): `clamp(25px, 3vw, 36px)`, ağırlık 700, satır yüksekliği 1.15.
- Üst etiket (eyebrow): 14 px, büyük harf, `letter-spacing: .12em`, ağırlık 700, renk `--muted`.
- Giriş paragrafı: 16 px, renk `--muted`, satır yüksekliği 1.6, azami genişlik ~960 px.
- Form etiketi: 13 px, ağırlık 700, renk `--text`.
- Metodoloji notu: 14 px, renk `--muted`, satır yüksekliği 1.65.
- Grafik başlığı: 20–21 px, renk `--text`.

## 3. Kart, Panel ve Yerleşim

- Arka plan beyaz, kenarlık `1px solid #E5E7EB`, köşe yuvarlatma **10 px**.
- Panel / metrik kartı gölgesi: `0 4px 6px -1px rgba(0,0,0,.1), 0 2px 4px -1px rgba(0,0,0,.06)`.
- Ana sayfa kartı gölgesi: `0 4px 8px rgba(0,0,0,.05)`; hover: `translateY(-2px)` ve `0 8px 18px rgba(0,0,0,.08)`.
- Sayfa kapsayıcısı: `max-width: 1600px`, ortalanmış, iç boşluk 24 px (900 px altında 14 px).
- Panel iç boşluğu: 16 px (900 px altında 12 px). Paneller arası boşluk: 18 px.
- Kontrol (dropdown) satırı: flex, `flex-wrap`, `gap: 18px`; tek kontrol genişliği ~300–420 px.
- Metrik kartları: 3 sütunlu grid, `gap: 14px`, kart iç boşluğu `17px 19px`.
- Ana sayfa kart gridi: 3 sütun, `gap: 18px`.
- Mobil kırılımlar: `900px` ve `700px` (modüllere göre), ana sayfa için ayrıca `600px`.
- Grafik yükseklikleri: G07 680 px, G08 600 px, G11 560 px (mobilde biraz daha düşük/yüksek olabilir).

## 4. Ortak Bileşenler

- **Metrik kartı:** Her zaman `pages/common.py` içindeki `make_metric_card(label, value, description)` kullanılır.
  Sınıflar: `metric-card`, `metric-label`, `metric-value`, `metric-description`; kapsayıcı `metrics`.
- **Geri bağlantısı:** `← Back to Dashboard Hub`, sınıf `hub-back`.
- **Modül iskeleti:** `<modül>-dashboard` > `<modül>-header` (eyebrow + H1 + intro) > metrik kartları > kontrol paneli > grafik paneli > `<modül>-method-note`.
- **Dropdown:** `dcc.Dropdown`, `clearable=False`, `searchable=True`, etiket `<modül>-label`.
- **Modül yapısı:** `load_data()`, `build_layout()`, `register_callbacks()`; hata için `DataValidationError`.

## 5. Plotly Grafik Standartları

- `paper_bgcolor = #F3F4F6`, `plot_bgcolor = #FFFFFF`.
- Izgara `#E5E7EB`, eksen çizgisi `#D1D5DB`, metin `#1F2937`, ikincil metin `#6B7280`.
- Başlık: `x=0.02`, `y=0.99`, `xanchor="left"`, `yanchor="top"`.
  **`layout.title.y` yalnızca 0–1 aralığında olmalıdır** (1.22 gibi değerler `ValueError` verir).
- Alt başlık / açıklama: `layout.annotations` ile, `yref="paper"`, `y=1.0`, `yanchor="bottom"` ve piksel bazlı `yshift`.
- Lejant: yatay, `y=1.0`, `yanchor="bottom"`, `x=0`, başlıksız.
- Üst boşluk (`margin.t`): 120–150 px; başlık, alt başlık ve lejant ayrı bantlarda durur.
- Sağ kenarda değer etiketi varsa `margin.r` genişletilir (G07'de 170 px) ve etiketler kırpılmamalıdır.
- Hover: çok serili grafiklerde `hovermode="x unified"`.
- Mobilde `displayModeBar=False`, `responsive=True`.

## 6. Anlamsal Renk Kuralları

### Pozitif / Negatif (G08, G09)

| Değer türü | Renk |
|---|---|
| Pozitif | Mavi `#0072B2` |
| Negatif | Kırmızı `#C62828` |

Turuncu negatif değer rengi kaldırılmıştır. Seri ayrımı için kırmızı kullanılırken bu anlam karışmamasına dikkat edilir.

### Tarihsel ve Projeksiyon

- Gözlenen / tarihsel değerler: düz çizgi.
- BM projeksiyonları: kesikli çizgi, grafikte gri gölgeli bölge ve "Projection" etiketi.
- Güven aralıkları (G07): aynı mavi tonu, iki saydamlık (95 % için `rgba(0,114,178,.12)`, 80 % için `rgba(0,114,178,.25)`), dış sınırlar ince kesikli gri.

### İki Seri Karşılaştırması (G11)

| Seri | Renk |
|---|---|
| Ülke A | `#0072B2` |
| Ülke B | `#7B1113` |

### Demografik Küme Renkleri (G02, G10)

| Küme | Ad | Renk |
|---|---|---|
| 1 | Pre-transition | `#2166AC` |
| 2 | Early transition | `#67A9CF` |
| 3 | Mid-transition | `#D9D9D9` |
| 4 | Late-transition | `#EF8A62` |
| 5 | Post-transition | `#B2182B` |

## 7. Modüllere Özel Paletler (koddan çıkarılan renkler)

| Modül | Öne çıkan renkler |
|---|---|
| G01 | Okabe–Ito paleti: `#0072B2`, `#E69F00`, `#009E73`, `#D55E00`, `#CC79A7`, `#56B4E9` |
| G02 | Küme renkleri (bölüm 6) |
| G03 | Küme renkleri + akışlar için turuncu ardışık ton: `#FDD0A2`, `#FDAE6B`, `#F16913`, `#8C2D04`; vurgu `#7B1113` |
| G04 | Ortak gri tonlar; vurgu `#D32F2F` |
| G05 | Mavi ardışık ton: `#9ECAE1`, `#4292C6`, `#084594`; ana seri `#0072B2` |
| G06 | Okabe–Ito renkleri + gri tonlar `#9CA3AF`, `#B7BEC8` |
| G07 | `#0072B2` (medyan ve bantlar), `#9CA3AF` (sınır çizgileri) |
| G08 | Pozitif `#0072B2`, negatif `#C62828` |
| G09 / G09B | `#7B1113`, `#3F4852`, Okabe–Ito renkleri, negatif `#C62828` |
| G10 | Küme renkleri (bölüm 6) |
| G11 | `#0072B2` ve `#7B1113` |

## 8. Bilinen Tutarsızlıklar (ileride hizalanabilir)

- G10 kendi CSS bloğunu kullanıyor: filtre paneli `#F7F9FC`, köşe yuvarlatma 14–16 px, eyebrow rengi mavi (`#3475B9`). Diğer modüller ortak token'ları ve 10 px köşeyi kullanıyor.
- G04'te vurgu rengi `#D32F2F`; negatif standardı `#C62828`.
- Grafik içi yazı tipi Arial, sayfa yazı tipi Inter.

## 9. Geliştirme İlkeleri

1. Mevcut Hub mimarisi ve her modülün analiz/grafik yapısı korunur.
2. Yeni veri dosyaları `data/out/` klasöründen okunur.
3. Ortak CSS ve tasarım sistemi korunur; yeni modül için `g<NN>-*` sınıf bloğu eklenir.
4. Başlık, açıklama ve lejant arasında yeterli boşluk bırakılır; değer etiketleri kırpılmaz.
5. Ülke seçimi olan modüllerde varsayılan ülke Türkiye'dir.
6. Pozitif/negatif renk standardı tüm ilgili grafiklerde tutarlıdır.
7. Her değişiklikten sonra Python sözdizimi ve Dash uygulama kontrolü yapılır.
8. Yalnızca talep edilen geliştirmeler uygulanır.