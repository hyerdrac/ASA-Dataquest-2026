from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "g09_bm_varsayim.csv"
RECOVERY_FILE = PROJECT_DIR / "data" / "out" / "g09b_dogurganlik_toparlanma.csv"
RECOVERY_SUMMARY_FILE = PROJECT_DIR / "data" / "out" / "g09b_toparlanma_ozet.csv"
BG, PANEL, TEXT, MUTED, GRID, BORDER = "#F3F4F6", "#FFFFFF", "#1F2937", "#6B7280", "#E5E7EB", "#D1D5DB"
POSITIVE, NEGATIVE, NEUTRAL = "#0072B2", "#C62828", "#9CA3AF"

# Display-only translations based on the complete unique-value lists supplied for G09.
# Original values remain unchanged for filtering and calculations.
TRANSLATIONS = {
    "BM kendi %95 alt sınırı (doğurganlık)": "UN own 95% lower bound (fertility)",
    "BM kendi %95 üst sınırı (doğurganlık)": "UN own 95% upper bound (fertility)",
    "Doğurganlık 2024 düzeyinde sabit kalsaydı": "Fertility remained at its 2024 level",
    "Doğurganlık medyandan 0,5 yüksek olsaydı": "Fertility 0.5 above the median",
    "Doğurganlık medyandan 0,5 düşük olsaydı": "Fertility 0.5 below the median",
    "Net göç sıfır olsaydı": "Net migration were zero",
    "Yaşam beklentisi artmasaydı (ölüm sabit)": "Life expectancy did not increase (constant mortality)",
    "Belirsizlik": "Uncertainty", "Doğurganlık": "Fertility", "Göç": "Migration", "Ölüm": "Mortality",
    "Net göç": "Net migration", "Yaşam beklentisi": "Life expectancy", "çocuk/kadın": "children per woman",
    "bin kişi/yıl": "thousand people per year", "yıl": "years",
    "Country/Area": "Country/Area", "Geographic region": "Geographic region", "World": "World",
}

def display(value) -> str:
    s = "" if value is None else str(value)
    for source in sorted(TRANSLATIONS, key=len, reverse=True):
        s = s.replace(source, TRANSLATIONS[source])
    return s

REQUIRED_COLUMNS = {
    "LocID", "LocTypeName", "Location", "Time", "Tip", "Gosterge", "Birim",
    "Baslangic_2024", "BM_degeri", "Alternatif", "Alternatif_aciklama", "Alternatif_degeri",
    "Nufus_BM_milyon", "Nufus_alternatif_milyon", "Nufus_etkisi_milyon", "Nufus_etkisi_yuzde",
}

class DataValidationError(ValueError):
    pass

def _load_assumption_data() -> pd.DataFrame:
    if not DATA_FILE.is_file():
        raise DataValidationError(f"Required input file not found: {DATA_FILE}\nPlace g09_bm_varsayim.csv in the project's data/out/ folder.")
    try:
        df = pd.read_csv(DATA_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read G09 CSV: {exc}") from exc
    df.columns = df.columns.astype(str).str.strip()
    missing = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing:
        raise DataValidationError(f"{DATA_FILE.name} missing columns: {', '.join(missing)}")
    df = df.copy()
    for c in ("LocID", "Time", "Baslangic_2024", "BM_degeri", "Alternatif_degeri", "Nufus_BM_milyon", "Nufus_alternatif_milyon", "Nufus_etkisi_milyon", "Nufus_etkisi_yuzde"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ("Location", "LocTypeName", "Tip", "Gosterge", "Birim", "Alternatif", "Alternatif_aciklama"):
        df[c] = df[c].fillna("").astype(str).str.strip()
    df = df.dropna(subset=["Location", "Time", "Tip", "Nufus_BM_milyon"])
    df["Time"] = df["Time"].astype(int)
    if df.empty:
        raise DataValidationError("G09 CSV contains no usable rows.")
    return df.sort_values(["Location", "Time", "Tip", "Alternatif_aciklama"]).reset_index(drop=True)

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the original G09 assumptions plus the two required recovery datasets."""
    assumptions = _load_assumption_data()
    for path, label in ((RECOVERY_FILE, "G09B fertility recovery"),
                        (RECOVERY_SUMMARY_FILE, "G09B recovery summary")):
        if not path.is_file():
            raise DataValidationError(
                f"Required input file not found: {path}\\n"
                "Place both g09b CSV files in the project's data/out/ folder."
            )
    try:
        recovery = pd.read_csv(RECOVERY_FILE, low_memory=False)
        summary = pd.read_csv(RECOVERY_SUMMARY_FILE, low_memory=False)
    except Exception as exc:
        raise DataValidationError(f"Could not read G09B CSV files: {exc}") from exc

    recovery_required = {"iso3", "country", "year", "tfr", "is_projection",
                         "below_1_5_in_2023", "recovered_to_1_8"}
    summary_required = {"iso3", "country", "first_below_year", "min_tfr", "min_year",
                        "max_after_min", "tfr_2023", "change_27y"}
    missing_recovery = sorted(recovery_required - set(recovery.columns))
    missing_summary = sorted(summary_required - set(summary.columns))
    if missing_recovery or missing_summary:
        details = []
        if missing_recovery:
            details.append("g09b_dogurganlik_toparlanma.csv: " + ", ".join(missing_recovery))
        if missing_summary:
            details.append("g09b_toparlanma_ozet.csv: " + ", ".join(missing_summary))
        raise DataValidationError("G09B missing required columns: " + " | ".join(details))

    recovery = recovery.copy()
    for col in ("year", "tfr"):
        recovery[col] = pd.to_numeric(recovery[col], errors="coerce")
    for col in ("is_projection", "below_1_5_in_2023", "recovered_to_1_8"):
        recovery[col] = recovery[col].astype(str).str.strip().str.lower().map(
            {"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False}
        ).fillna(False)
    recovery["country"] = recovery["country"].fillna("").astype(str)
    recovery = recovery.dropna(subset=["iso3", "country", "year", "tfr"])
    recovery["year"] = recovery["year"].astype(int)

    summary = summary.copy()
    summary["change_27y"] = pd.to_numeric(summary["change_27y"], errors="coerce")
    if recovery.empty or summary.empty:
        raise DataValidationError("G09B files contain no usable rows.")
    return assumptions, recovery.sort_values(["iso3", "year"]).reset_index(drop=True), summary


def _layout(fig: go.Figure, title: str, ytitle: str = "") -> go.Figure:
    fig.update_layout(title=dict(text=title, x=.02, xanchor="left", font=dict(size=20, color=TEXT)),
        font=dict(family="Arial, sans-serif", color=TEXT, size=12), paper_bgcolor=BG, plot_bgcolor=PANEL,
        margin=dict(l=70, r=35, t=82, b=115), hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        xaxis=dict(title="", gridcolor=GRID, showline=True, linecolor=BORDER, zeroline=True, zerolinecolor=BORDER),
        yaxis=dict(title=ytitle, gridcolor=GRID, showline=True, linecolor=BORDER, automargin=True), showlegend=False)
    return fig

def _subset(df, location, year):
    return df[(df["Location"] == location) & (df["Time"] == int(year))].copy()

def build_effect_figure(data: pd.DataFrame, location: str, year: int) -> go.Figure:
    d = _subset(data, location, year).dropna(subset=["Nufus_etkisi_milyon"])
    fig = go.Figure()
    if d.empty:
        fig.add_annotation(text="No population-impact values available for this selection.", x=.5, y=.5, xref="paper", yref="paper", showarrow=False)
        return _layout(fig, f"Alternative assumptions · {location} · {year}", "Alternative assumption")
    d = d.sort_values("Nufus_etkisi_milyon")
    colors = [POSITIVE if x >= 0 else NEGATIVE for x in d["Nufus_etkisi_milyon"]]
    custom = [[display(r["Tip"]), display(r["Gosterge"]), display(r["Birim"]), r["Nufus_BM_milyon"], r["Nufus_alternatif_milyon"], r["Nufus_etkisi_yuzde"], display(r["Alternatif"])] for _, r in d.iterrows()]
    fig.add_trace(go.Bar(x=d["Nufus_etkisi_milyon"], y=[display(x) for x in d["Alternatif_aciklama"]], orientation="h",
        marker_color=colors, customdata=custom, text=[f"{x:+,.1f}M" for x in d["Nufus_etkisi_milyon"]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Assumption type: %{customdata[0]}<br>Indicator: %{customdata[1]} (%{customdata[2]})<br>Population impact: %{x:+,.3f} million<br>Impact: %{customdata[5]:+.2f}%<br>UN population: %{customdata[3]:,.2f} million<br>Alternative population: %{customdata[4]:,.2f} million<extra></extra>"))
    fig.add_vline(x=0, line_color=NEUTRAL, line_width=1)
    fig.update_layout(margin=dict(l=330, r=70, t=82, b=65), xaxis_title="Population impact versus UN projection (millions)", yaxis=dict(title="", gridcolor=GRID, automargin=True), height=max(480, 70*len(d)+150))
    fig = _layout(fig, f"Population impact of alternative assumptions · {location} · {year}")
    fig.update_xaxes(title_text="Population impact versus UN projection (millions)")
    return fig

def build_indicator_figure(data: pd.DataFrame, location: str, year: int) -> go.Figure:
    d = _subset(data, location, year).dropna(subset=["BM_degeri", "Alternatif_degeri"])
    fig = go.Figure()
    if d.empty:
        fig.add_annotation(text="No indicator comparison available for this selection.", x=.5, y=.5, xref="paper", yref="paper", showarrow=False)
        return _layout(fig, f"Assumption values · {location} · {year}")
    labels = [f"{display(r['Gosterge'])} · {display(r['Alternatif'])}" for _, r in d.iterrows()]
    # Each row is its own paired comparison because indicator units differ.
    for i, (_, r) in enumerate(d.iterrows()):
        fig.add_trace(go.Scatter(x=[float(r["BM_degeri"]), float(r["Alternatif_degeri"])], y=[labels[i], labels[i]], mode="lines+markers",
            line=dict(color=POSITIVE if float(r["Alternatif_degeri"]) >= float(r["BM_degeri"]) else NEGATIVE, width=3),
            marker=dict(size=9), name=labels[i], showlegend=False,
            customdata=["UN value", "Alternative value"],
            hovertemplate=f"{labels[i]}<br>%{{customdata}}: %{{x:,.3f}}<extra></extra>"))
    fig.update_layout(height=max(360, 48*len(d)+140), margin=dict(l=330, r=40, t=75, b=70), xaxis_title="Indicator value (units vary by indicator)", yaxis=dict(title="", automargin=True, gridcolor=GRID), showlegend=False)
    fig = _layout(fig, f"UN vs. alternative assumption values · {location} · {year}")
    fig.update_xaxes(title_text="Indicator value (units vary by indicator)")
    return fig

def build_recovery_figure(recovery: pd.DataFrame, summary: pd.DataFrame) -> go.Figure:
    """Historical fertility paths and UN projections for countries below 1.5 in 2023."""
    fig = go.Figure()
    countries = recovery.groupby("iso3", sort=True)
    projection_colors = [
        "#2166AC", "#D55E00", "#009E73", "#CC79A7", "#7B1113",
        "#56B4E9", "#E69F00", "#6A3D9A", "#008B8B", "#A6761D",
    ]
    color_by_iso = {}
    eligible = recovery[recovery["below_1_5_in_2023"]]
    eligible_codes = sorted(eligible["iso3"].unique())
    color_by_iso = {code: projection_colors[i % len(projection_colors)]
                    for i, code in enumerate(eligible_codes)}
    recovered = set(recovery.loc[recovery["recovered_to_1_8"], "iso3"].unique())

    # Historical observations: all 51 countries, shown as fine gray trajectories.
    for iso3, country_df in countries:
        hist = country_df[~country_df["is_projection"] & (country_df["year"] <= 2023)]
        if hist.empty:
            continue
        country = str(hist["country"].iloc[0])
        is_recovered = iso3 in recovered
        fig.add_trace(go.Scatter(
            x=hist["year"], y=hist["tfr"], mode="lines",
            name=country if is_recovered else country,
            line=dict(color="#59636F" if is_recovered else "#B8BEC6",
                      width=2.0 if is_recovered else 0.8),
            opacity=0.95 if is_recovered else 0.65,
            showlegend=False,
            hovertemplate=f"<b>{country}</b><br>Year: %{{x}}<br>Fertility: %{{y:.2f}}<extra></extra>",
        ))

    # UN projection: only the 41 countries below 1.5 children per woman in 2023.
    for iso3 in eligible_codes:
        country_df = recovery[(recovery["iso3"] == iso3) & recovery["is_projection"]]
        if country_df.empty:
            continue
        country = str(country_df["country"].iloc[0])
        is_recovered = iso3 in recovered
        fig.add_trace(go.Scatter(
            x=country_df["year"], y=country_df["tfr"], mode="lines",
            name=country,
            line=dict(color="#3F4852" if is_recovered else color_by_iso[iso3],
                      width=3.0 if is_recovered else 1.7, dash="dash"),
            opacity=1,
            showlegend=is_recovered,
            hovertemplate=f"<b>{country} · UN projection</b><br>Year: %{{x}}<br>Fertility: %{{y:.2f}}<extra></extra>",
        ))
        if is_recovered:
            last = country_df.sort_values("year").iloc[-1]
            fig.add_annotation(
                x=int(last["year"]), y=float(last["tfr"]), xref="x", yref="y",
                text=country, showarrow=False, xshift=8, yshift=0,
                xanchor="left", font=dict(size=11, color="#3F4852"),
            )

    # Keep the two reference thresholds visually distinct and label replacement level.
    fig.add_hline(y=1.5, line=dict(color="#9CA3AF", width=1, dash="dot"),
                  annotation_text="1.5", annotation_position="top left",
                  annotation_font=dict(size=10, color="#6B7280"))
    fig.add_hline(y=2.1, line=dict(color="#7B1113", width=1.4, dash="dash"),
                  annotation_text="2.1 · replacement level",
                  annotation_position="top left",
                  annotation_font=dict(size=11, color="#7B1113"))

    valid_changes = summary["change_27y"].dropna()
    historical_share = (valid_changes.gt(0).mean() * 100) if not valid_changes.empty else 52
    fig.update_layout(
        title=dict(
            text="Historically, half of these countries recovered; the UN assumes all will recover",
            x=0.02, xanchor="left", y=0.98,
            font=dict(size=19, color=TEXT),
        ),
        font=dict(family="Arial, sans-serif", color=TEXT, size=11),
        paper_bgcolor=BG, plot_bgcolor=PANEL,
        margin=dict(l=65, r=175, t=105, b=62),
        height=650,
        hoverlabel=dict(bgcolor="#FFFFFF", font_size=12),
        xaxis=dict(title="Year", range=[1950, 2108], dtick=10,
                   gridcolor=GRID, showline=True, linecolor=BORDER),
        yaxis=dict(title="Total fertility rate (children per woman)",
                   range=[0, max(3.5, float(recovery["tfr"].max()) * 1.03)],
                   gridcolor=GRID, showline=True, linecolor=BORDER),
        annotations=list(fig.layout.annotations or []) + [
            dict(
                x=1.015, y=0.98, xref="paper", yref="paper",
                xanchor="left", yanchor="top", showarrow=False,
                align="left", bgcolor="#F7F9FC",
                bordercolor="#E5E7EB", borderwidth=1, borderpad=10,
                text=(f"<b>Share of countries with rising fertility<br>over the next 27 years</b>"
                      f"<br><br>Historical: {historical_share:.0f}%"
                      f"<br>UN projection: 100%"),
                font=dict(size=11, color=TEXT),
            )
        ],
        showlegend=True,
        legend=dict(orientation="h", y=-0.18, x=0, title_text="Historically recovered countries"),
    )
    return fig


def _kpis(df, location, year):
    d = _subset(df, location, year)
    if d.empty: return "—", "—", "—"
    baseline = float(d["Nufus_BM_milyon"].dropna().iloc[0]) if d["Nufus_BM_milyon"].notna().any() else float("nan")
    effects = d["Nufus_etkisi_milyon"].dropna()
    if effects.empty: return f"{baseline:,.2f}M", "—", "0"
    max_abs = effects.abs().idxmax()
    strongest = d.loc[max_abs]
    return f"{baseline:,.2f}M", f"{float(strongest['Nufus_etkisi_milyon']):+,.2f}M", str(len(effects))

def build_layout(df: pd.DataFrame, recovery: pd.DataFrame, recovery_summary: pd.DataFrame, show_back_link: bool = True):
    locations = sorted(df["Location"].dropna().unique().tolist())
    default_location = "Türkiye" if "Türkiye" in locations else ("World" if "World" in locations else locations[0])
    locdf = df[df["Location"] == default_location]
    years = sorted(locdf["Time"].unique().tolist())
    default_year = 2050 if 2050 in years else int(years[-1])
    k1, k2, k3 = _kpis(df, default_location, default_year)
    children=[]
    if show_back_link: children.append(html.A("← Back to Dashboard Hub", href="/", className="hub-back"))
    children.extend([
        html.Header(className="g09-header", children=[html.Div("G09 · UN ASSUMPTION CHECK", className="g09-eyebrow"), html.H1("What if UN assumptions were different?"),
            html.P("Compare the UN population projection with alternative fertility, migration, mortality and uncertainty assumptions. Values are translated for display; the source CSV remains unchanged.", className="g09-intro")]),
        html.Section(className="metrics g09-metrics", children=[
            html.Div([html.Div("UN projected population", className="metric-label"), html.Div(k1, id="g09-kpi-baseline", className="metric-value"), html.Div("Millions of people", className="metric-description")], className="metric-card"),
            html.Div([html.Div("Largest absolute impact", className="metric-label"), html.Div(k2, id="g09-kpi-impact", className="metric-value"), html.Div("Among available alternatives", className="metric-description")], className="metric-card"),
            html.Div([html.Div("Available comparisons", className="metric-label"), html.Div(k3, id="g09-kpi-count", className="metric-value"), html.Div("Rows with population impact", className="metric-description")], className="metric-card")]),
        html.Section(className="g09-panel", children=[html.Div(className="g09-controls", children=[
            html.Div([html.Label("Location", htmlFor="g09-location", className="g09-label"), dcc.Dropdown(id="g09-location", options=[{"label": x, "value": x} for x in locations], value=default_location, clearable=False, searchable=True)], className="g09-control"),
            html.Div([html.Label("Projection year", htmlFor="g09-year", className="g09-label"), dcc.Dropdown(id="g09-year", options=[{"label": str(int(y)), "value": int(y)} for y in sorted(df["Time"].unique())], value=default_year, clearable=False)], className="g09-control")])]),
        html.Section(className="g09-panel g09-recovery-panel", children=[
            dcc.Graph(id="g09-recovery-chart", figure=build_recovery_figure(recovery, recovery_summary),
                      config={"displayModeBar": False, "responsive": True},
                      style={"height": "650px", "minHeight": "650px", "width": "100%"})
        ]),
        html.Section(className="g09-panel g09-chart-panel", children=[dcc.Graph(id="g09-impact-chart", figure=build_effect_figure(df, default_location, default_year), config={"displayModeBar": False, "responsive": True}, style={"height":"auto", "minHeight":"480px", "width":"100%"})]),
        html.Section(className="g09-panel g09-chart-panel", children=[dcc.Graph(id="g09-indicator-chart", figure=build_indicator_figure(df, default_location, default_year), config={"displayModeBar": False, "responsive": True}, style={"height":"auto", "minHeight":"400px", "width":"100%"})]),
        html.P("Reading note: population impact is the alternative population minus the UN projection, in millions. Positive values indicate a higher population than the UN projection; negative values indicate a lower population. Indicator values may use different units, so compare them within each indicator only.", className="g09-method-note")])
    return html.Main(className="g09-dashboard", children=children)

def register_callbacks(app, df: pd.DataFrame) -> None:
    @app.callback(Output("g09-impact-chart", "figure"), Output("g09-indicator-chart", "figure"), Output("g09-kpi-baseline", "children"), Output("g09-kpi-impact", "children"), Output("g09-kpi-count", "children"), Input("g09-location", "value"), Input("g09-year", "value"))
    def update_g09(location, year):
        if location not in set(df["Location"].unique()): location = sorted(df["Location"].unique())[0]
        locyears = sorted(df.loc[df["Location"] == location, "Time"].unique())
        if year not in locyears: year = 2050 if 2050 in locyears else int(locyears[-1])
        k1, k2, k3 = _kpis(df, location, int(year))
        return build_effect_figure(df, location, int(year)), build_indicator_figure(df, location, int(year)), k1, k2, k3
