# ASA Dataquest 2026 - Data-wan Kenobi Team Solutions

## 📌 Overview

An analysis of the UN World Population Prospects 2024 dataset: 237 countries and areas, 1950–2100, covering population, fertility, mortality and migration indicators.

## 🎯 Problem Statement

<!-- To be completed -->

## 💡 Our Solution

<!-- To be completed -->

## 🏆 Competition Details

- **Competition:** ASA Dataquest 2026
- **Category:** Datathon
- **Team Name:** Data-wan Kenobi
- **Submission Date:** 31/10/2026

## 👥 Team Members

| Name | Role | GitHub |
|---|---|---|
| Yiğit Taha Ak | Analysis Lead | [ytafk](https://github.com/ytafk) |
| Hasan Furkan Koca | Scenario Analyst | [FURKAN3312](https://github.com/FURKAN3312) |
| Taha Mert İlhan | Analysis & Validation | [aem0n](https://github.com/aem0n) |
| Hakan Yerdraç | Lead Visualization & Presentation | [hyerdrac](https://github.com/hyerdrac) |

## 📂 Project Structure

```text
ASA-Dataquest-2026/
├── data/
│   ├── raw/           # Raw data given by the competition (not tracked by git)
│   ├── clean/         # Cleaned data for analysis
│   └── out/           # Chart-ready outputs of each analysis (gNN_short_name.csv)
├── documents/         # Competition documents
├── scripts/           # Data preparation scripts
├── notebooks/         # Experiments and analysis
├── dashboard/         # Dashboard app
├── charts/            # Exported charts
├── deck/              # Presentation
├── requirements.txt   # Project dependencies
├── .gitignore
├── README.md
└── bulgular.md        # One-sentence finding for each chart
```

## ⚙️ Setup

1. Clone the repository.
2. Put the UN raw files into `data/raw/`. This folder is not pushed to GitHub because the files are too large (OtherVariants is ~230 MB; GitHub's limit is 100 MB):
   - `WPP2024_Demographic_Indicators_Medium_csv`
   - `WPP2024_Demographic_Indicators_OtherVariants_csv`
   - `WPP2024_Supplement_Births_and_LE60.csv`
3. Create the Python environment (Windows):

   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## 🧹 How the Clean Data Is Produced

The shared data is never edited by hand. It is always regenerated with these two commands:

```
python scripts\prepare.py data\raw\WPP2024_Demographic_Indicators_Medium_csv data\raw\WPP2024_Supplement_Births_and_LE60.csv data\clean\countries_clean.csv
python scripts\make_country_list.py data\clean\countries_clean.csv data\clean\ulkeler_1m.csv
```

Expected output: `(36024, 68) 0 eksik bölge` and `161 ülke yazıldı`.

### What `prepare.py` does

1. **Keeps only actual countries.** The Medium file has 555 locations: 237 countries/areas and 318 groupings (regions, income groups, EU, BRICS, etc.). Summing groupings together with countries would count the same people several times. `ISO3_code` is filled only for countries, so we filter on it. Check: the population of the 237 countries equals the `World` row exactly, every year.
2. **Adds region information.** Each country's `ParentID` points to its UN subregion, and each subregion to its region. New columns: `Subregion`, `Region` (the 6 UN regions) and `Continent`. The Northern America subregion (ID 918) has no row of its own in the file, so it is filled in manually.
3. **Separates estimates from projections.** `IsProjection` is `False` for 1950–2023 (UN estimates) and `True` from 2024 on (projections).
4. **Merges the supplementary file.** `BirthsMale`, `BirthsFemale`, `LE60`, `LE60Male` and `LE60Female` from the supplement provided by the competition are joined on `LocID` and `Time`.
5. **Drops unused columns:** `SortOrder`, `Notes`, `ISO2_code`, `SDMX_code`, `LocTypeID`, `LocTypeName`, `VarID`, `Variant`.

Result: 237 countries × 152 years (1950–2101) = 36,024 rows, 68 columns.

### Known gaps

- **2101:** Only the 1 January population is available; every other indicator is empty. Analyses stop at 2100.
- **Holy See:** Not in the supplementary file, so its supplement columns are empty.
- **Regions:** We use the UN's regional classification, which places Türkiye in Western Asia.

### What `make_country_list.py` does

Lists the 161 countries with a 2024 population above 1 million. Analyses such as clustering use this list, because the volatile values of very small countries distort the results. Keeping it in a separate file means the definition of a "large country" lives in one place.

## 📚 Source

United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition. CC BY 3.0 IGO.
