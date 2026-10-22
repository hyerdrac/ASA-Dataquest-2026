# Yöntem: Kümeleme ve zaman makinesi

Bu belge, analiz liderinin kümeleme ve zaman makinesi sonuçlarını **kodunu görmeden** yeniden üretebilmeniz için yazıldı. Doğrulama yapacaksanız önce 1–3. bölümlere göre kendi kodunuzu yazın, sonuçlarınızı hesaplayın ve **ancak ondan sonra** 4. bölümdeki değerlerle karşılaştırın.

## 1. Veri

- Girdi: `data/clean/countries_clean.csv` ve `data/clean/ulkeler_1m.csv`.
- Ülkeler: `ulkeler_1m.csv` içindeki 161 ülke (2024 nüfusu 1 milyonun üstünde). Eşleştirme `ISO3_code` = `iso3` ile.
- Yıllar: 1950–2023 (dahil). 2024 ve sonrası BM projeksiyonu olduğu için model kurulurken kullanılmaz.
- Sonuç: 161 × 74 = 11.914 satır, boş değer yok.

## 2. Kümeleme

| Karar | Değer | Gerekçe |
| --- | --- | --- |
| Analiz birimi | Ülke-yıl (bütün yıllar tek seferde) | Kümeler her yıl aynı anlamı taşısın; yıllar arası geçiş karşılaştırılabilsin |
| Özellikler | `TFR`, `LEx`, `MedianAgePop` | Doğurganlık, ölüm ve yaş yapısı |
| Dışarıda bırakılanlar | `IMR` ve `CNMR` | `log(IMR)` ile `LEx` korelasyonu −0,91 (aynı boyutun tekrarı); göç eklenince demografik basamaklar yerine Körfez ülkelerini ayıran bir küme çıkıyor |
| Ölçekleme | `StandardScaler` (z-skor), 11.914 satırın tamamına uydurulur | Ölçeklenmezse yaşam beklentisi doğurganlığı ezer |
| Algoritma | `KMeans(n_clusters=5, random_state=42, n_init=50)` | `n_init=50` ile farklı başlangıçlarda sonuç değişmiyor (ARI 0,98–1,00) |
| Küme sayısı | 5 | Silüet skoru k=3'te en yüksek, ama 5 basamak geçişi anlatmaya yetiyor ve 0,38 kabul edilebilir |
| Etiketleme | Kümeler ortalama `TFR`'ye göre azalan sırada 1–5 numaralanır | K-means'in ham etiketleri her çalıştırmada değişebilir |

Küme isimleri: 1 Geçiş öncesi · 2 Erken geçiş · 3 Orta geçiş · 4 Geç geçiş · 5 Geçiş sonrası

## 3. Zaman makinesi

| Karar | Değer |
| --- | --- |
| Özellikler ve ölçekleme | Kümelemedekiyle aynı üç özellik, aynı ölçekleyici (1950–2023 verisine uydurulmuş) |
| Sorgu | Türkiye'nin ilgili yıldaki değerleri (2024 sonrası BM orta senaryosu) |
| Aday havuzu | Türkiye dışındaki 160 ülkenin yalnızca 1950–2023 değerleri |
| Mesafe | Z-skor uzayında Öklid mesafesi |
| Ülke başına | Her aday ülkenin yalnızca en yakın yılı |
| Eşik | 1950–2023'teki her ülke-yılın, **başka bir ülkedeki** en yakın gözleme mesafesinin %95'lik dilimi |
| "İkiz bölgesi" | Mesafesi eşiğin altında kalan bütün ülke-yıllar |
| "İkizsiz yıl" | En yakın adayın bile eşiğin üstünde kaldığı yıl |

## 4. Karşılaştırma değerleri (kendi hesabınızdan sonra bakın)

### Kümeleme

Küme ortalamaları (1950–2023, ülke-yıl ortalaması):

| Küme | TFR | LEx | MedianAgePop | Gözlem |
| --- | --- | --- | --- | --- |
| 1 | 6,71 | 42,30 | 17,27 | 2362 |
| 2 | 6,01 | 56,55 | 16,72 | 2668 |
| 3 | 3,71 | 65,16 | 19,89 | 2291 |
| 4 | 2,31 | 71,62 | 28,29 | 2843 |
| 5 | 1,54 | 77,10 | 37,48 | 1750 |

- Silüet skorları (k=3…8; k taraması `KMeans(random_state=42, n_init=10)` ile, `silhouette_score(sample_size=5000, random_state=42)`): 0,478 · 0,425 · 0,382 · 0,360 · 0,332 · 0,309
- Kümelerdeki ülke sayısı, 1990: {1: 22, 2: 39, 3: 40, 4: 38, 5: 22}
- Kümelerdeki ülke sayısı, 2023: {2: 8, 3: 44, 4: 42, 5: 67}
- 1990→2023 arasında daha alt kümede biten ülke sayısı: 0
- Yıllık geri düşüş: 44 kez, 32 ülkede
- Türkiye'nin küme değişimleri: 1950: 1 · 1959: 2 · 1977: 3 · 1997: 4 · 2022: 5

### Zaman makinesi

- Eşik: 0,149 (%90 = 0,110 · %99 = 0,257)
- Türkiye 2023 → en yakın: Hollanda 1987 (0,04)
- Türkiye 2050 → ikiz bölgesi (6): Slovenya 2023, Portekiz 2019, Japonya 2011, İtalya 2015, Almanya 2019, Yunanistan 2020
- Türkiye 2075 → en yakın: Japonya 2023, ama mesafe 0,44 (eşiğin üstünde)
- İlk ikizsiz yıl: 2061 (eşik %90 → 2052, %99 → 2068)
- Türkiye'nin medyan yaşı, 1950–2023'teki en yüksek değeri (49,0, Japonya 2023) 2064'te aşıyor

### Tolerans

Paket sürümlerine bağlı olarak silüet skorlarında ve küme ortalamalarında üçüncü ondalıkta fark olabilir. Bunun ötesindeki her fark konuşulmalı.

## 5. Sağlamlık: hangi bulgular kullanılabilir?

| Bulgu | Durum |
| --- | --- |
| 2023'te ilk basamakta hiçbir ülke yok | Sağlam (6 varyantın hepsinde) |
| 1990–2023 arasında hiçbir ülke daha alt basamakta bitirmedi | Sağlam (6 varyantın 5'inde; göç eklenince 2) |
| Türkiye hiç geri adım atmadan tırmandı | Sağlam (Ward dahil 7 yöntemin hepsinde) |
| 1950'de 93 ülke ilk basamaktaydı | Sayı varyanta göre 84–101; "yarısından fazlası" diye kullanın |
| Türkiye 5 basamağın hepsinden geçen 12 ülkeden biri | Sağlam değil; kullanmayın |
| Türkiye son basamağa 2022'de ulaştı | Sağlam değil (2005–2022); kullanmayın |
| 2050 ikizleri bugünün Güney ve Orta Avrupa'sı | Grup olarak sağlam; tek bir ülke adı olarak değil |
| 2061'den sonra tarihte benzeri yok | Eşiğe göre 2052–2068; "2060'lardan itibaren" demek en güvenlisi |

Ayrıntılar: `notebooks/04_saglamlik.ipynb`, `data/out/saglamlik_kumeleme.csv`.
