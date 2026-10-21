"""DataQuest 2026 - WPP2024 temiz ülke tablosu.
Girdi: Medium csv + Supplement csv. Çıktı: out/countries_clean.csv
"""
import sys, pandas as pd
MED, SUP, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
m = pd.read_csv(MED, encoding="utf-8-sig", low_memory=False)
locs = m.drop_duplicates("LocID").set_index("LocID")
c = m[m.ISO3_code.notna()].copy()                     # 237 ülke/alan; toplamı = World
# Bölge eşlemesi: ülke -> alt bölge -> bölge (918 = Northern America, dosyada satırı yok)
sub_name = locs.Location.to_dict(); sub_name[918] = "Northern America"
sub_parent = locs.ParentID.to_dict(); sub_parent[918] = 905
c["Subregion"] = c.ParentID.map(sub_name)
reg_id = c.ParentID.map(sub_parent)
c["Region"] = reg_id.map(sub_name)
c["Continent"] = c.Region.replace({"Latin America and the Caribbean": "Americas", "Northern America": "Americas"})
c["IsProjection"] = c.Time >= 2024
s = pd.read_csv(SUP)
c = c.merge(s.drop(columns=["ISO3_code", "Location"]), on=["LocID", "Time"], how="left")
drop = ["SortOrder", "Notes", "ISO2_code", "SDMX_code", "LocTypeID", "LocTypeName", "VarID", "Variant"]
c = c.drop(columns=drop)
front = ["LocID", "ISO3_code", "Location", "Subregion", "Region", "Continent", "Time", "IsProjection"]
c = c[front + [x for x in c.columns if x not in front]]
c.to_csv(OUT, index=False)
print(c.shape, c.Region.isna().sum(), "eksik bölge")
