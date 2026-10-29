from __future__ import annotations

from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_FILE = PROJECT_DIR / "data" / "out" / "g09_bm_varsayim.csv"
BG, PANEL, TEXT, MUTED, GRID, BORDER = "#F3F4F6", "#FFFFFF", "#1F2937", "#6B7280", "#E5E7EB", "#D1D5DB"
POSITIVE, NEGATIVE, NEUTRAL = "#0072B2", "#D55E00", "#9CA3AF"

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

def load_data() -> pd.DataFrame:
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

def _kpis(df, location, year):
    d = _subset(df, location, year)
    if d.empty: return "—", "—", "—"
    baseline = float(d["Nufus_BM_milyon"].dropna().iloc[0]) if d["Nufus_BM_milyon"].notna().any() else float("nan")
    effects = d["Nufus_etkisi_milyon"].dropna()
    if effects.empty: return f"{baseline:,.2f}M", "—", "0"
    max_abs = effects.abs().idxmax()
    strongest = d.loc[max_abs]
    return f"{baseline:,.2f}M", f"{float(strongest['Nufus_etkisi_milyon']):+,.2f}M", str(len(effects))

def build_layout(df: pd.DataFrame, show_back_link: bool = True):
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
