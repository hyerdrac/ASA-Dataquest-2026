"""Ekibin ortak "büyük ülke" listesi: 2024 nüfusu 1 milyonun üstündeki ülkeler.

Kullanım:
    python scripts/make_country_list.py data/clean/countries_clean.csv data/clean/ulkeler_1m.csv
"""
import sys
import pandas as pd

GIRDI, CIKTI = sys.argv[1], sys.argv[2]
ESIK_BIN = 1000  # TPopulation1July bin kişi cinsinden; 1000 = 1 milyon

c = pd.read_csv(GIRDI, usecols=["ISO3_code", "Location", "Region", "Time", "TPopulation1July"])
y = c[(c.Time == 2024) & (c.TPopulation1July > ESIK_BIN)]

liste = pd.DataFrame({
    "iso3": y.ISO3_code,
    "country": y.Location,
    "region": y.Region,
    "pop_2024_millions": (y.TPopulation1July / 1000).round(2),
}).sort_values("pop_2024_millions", ascending=False)

liste.to_csv(CIKTI, index=False)
print(len(liste), "ülke yazıldı ->", CIKTI)
