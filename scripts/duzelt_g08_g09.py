"""g08 şelale ayrıştırmasının yönünü ve işaretini düzeltir; g09'dan hatalı 'Belirsizlik' satırlarını çıkarır.

Neden:
- Eski ayrıştırma BM tahmininden (Median PI) başlayıp etkenleri tek tek KALDIRIYORDU
  (Median → Zero migration → Instant replacement zero migration → Momentum).
  Bu yüzden her çubuk etkenin kendisini değil, kaldırılmasının etkisini gösteriyordu
  ve işaretler ters okunuyordu (ör. Türkiye 2100 "Göç etkisi +14,1" ama göç nüfusu 14,1 M azaltıyor).
- Yeni ayrıştırma Momentum'dan başlar ve etkenleri tek tek EKLER:
  Momentum → (+ölüm iyileşmesi) Instant replacement zero migration → (+gerçek doğurganlık) Zero migration
  → (+göç) Median PI. Büyüklükler aynıdır, yalnızca sıra ve işaret değişir.
- g09'daki 'Belirsizlik' satırları doğurganlığın %95 sınırını nüfusun %95 sınırıyla eşleştiriyordu.
  Olasılıksal aralıklar her gösterge için ayrı hesaplandığından bu eşleştirme geçersizdir; belirsizliği g07 gösteriyor.

Kullanım:  python scripts/duzelt_g08_g09.py
"""
from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "out"
G08, G09 = OUT / "g08_selale.csv", OUT / "g09_bm_varsayim.csv"

s = pd.read_csv(G08)
eski = s[s.Tur == "Ayrıştırma"]
sen = s[s.Tur == "Senaryo"]
if set(eski.Adim) != {"1. Göç etkisi", "2. Doğurganlık etkisi", "3. Ölüm etkisi"}:
    raise SystemExit("g08 zaten düzeltilmiş ya da beklenmeyen biçimde; işlem yapılmadı.")

anahtar = ["LocID", "LocTypeName", "Location", "Time"]
p = sen.pivot_table(index=anahtar, columns="Adim", values="Nufus_milyon").reset_index()
med = sen.groupby(anahtar).Referans_milyon.first().rename("Median PI").reset_index()
p = p.merge(med, on=anahtar)

adimlar = [  # (Adim, Varsayim_grubu, sonuç senaryosu, referans senaryosu)
    ("1. Ölüm etkisi", "Ölüm", "Instant replacement zero migration", "Momentum"),
    ("2. Doğurganlık etkisi", "Doğurganlık", "Zero migration", "Instant replacement zero migration"),
    ("3. Göç etkisi", "Göç", "Median PI", "Zero migration"),
]
yeni = []
for adim, grup, sonuc, ref in adimlar:
    y = p[anahtar].copy()
    y["Tur"], y["Adim"], y["Varsayim_grubu"] = "Ayrıştırma", adim, grup
    y["Nufus_milyon"], y["Referans"], y["Referans_milyon"] = p[sonuc].round(3), ref, p[ref].round(3)
    y["Fark_milyon"] = (p[sonuc] - p[ref]).round(3)
    y["Fark_yuzde"] = ((p[sonuc] - p[ref]) / p[ref] * 100).round(2)
    yeni.append(y)
yeni = pd.concat(yeni)[s.columns]

# Kontrol 1: zincir kapanıyor mu? Momentum + etkiler = BM tahmini
k = yeni.groupby(anahtar).Fark_milyon.sum().reset_index().merge(p[anahtar + ["Momentum", "Median PI"]], on=anahtar)
kapanma = (k.Momentum + k.Fark_milyon - k["Median PI"]).abs().max()
# Kontrol 2: her etken eski değerin tam tersi mi?
eslesme = {"1. Ölüm etkisi": "3. Ölüm etkisi", "2. Doğurganlık etkisi": "2. Doğurganlık etkisi", "3. Göç etkisi": "1. Göç etkisi"}
kar = yeni.assign(eski_adim=yeni.Adim.map(eslesme)).merge(
    eski[anahtar + ["Adim", "Fark_milyon"]], left_on=anahtar + ["eski_adim"], right_on=anahtar + ["Adim"], suffixes=("", "_eski"))
ters = (kar.Fark_milyon + kar.Fark_milyon_eski).abs().max()
print(f"Satır: eski {len(eski)}, yeni {len(yeni)} | kapanma hatası {kapanma:.4f} M | işaret kontrolü {ters:.4f} M")
if len(yeni) != len(eski) or kapanma > 0.01 or ters > 0.01:
    raise SystemExit("Kontrol başarısız; dosyalar değiştirilmedi.")

pd.concat([sen, yeni]).to_csv(G08, index=False)

b = pd.read_csv(G09)
n = int((b.Tip == "Belirsizlik").sum())
b[b.Tip != "Belirsizlik"].to_csv(G09, index=False)
print(f"g09: {n} 'Belirsizlik' satırı çıkarıldı, {len(b) - n} satır kaldı.")

tr = yeni[(yeni.Location == "Türkiye") & (yeni.Time == 2100)]
print("\nTürkiye 2100 (Momentum'dan BM tahminine):")
print(tr[["Adim", "Referans", "Referans_milyon", "Fark_milyon", "Nufus_milyon"]].to_string(index=False))
