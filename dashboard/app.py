from __future__ import annotations

from dash import Dash, Input, Output, dcc, html

from pages import g01_shift, g02_map, g03_transitions, g04_twins, g05_survival, g06_migration_shield
from pages.g03_transitions import DataValidationError

# One central Dash server; the existing G03 chart functions remain in their module.
app = Dash(__name__, assets_folder="assets", suppress_callback_exceptions=True)
app.title = "Dashboard Hub"

try:
    G03_COUNTRIES, G03_FLOWS, G03_NOTE = g03_transitions.load_data()
    G03_ERROR = None
    g03_transitions.register_callbacks(app, G03_COUNTRIES)
except DataValidationError as exc:
    G03_COUNTRIES, G03_FLOWS, G03_NOTE = None, None, None
    G03_ERROR = str(exc)

try:
    G02_DATA = g02_map.load_data()
    G02_ERROR = None
except g02_map.DataValidationError as exc:
    G02_DATA = None
    G02_ERROR = str(exc)

try:
    G01_SHARE, G01_RANK = g01_shift.load_data()
    G01_ERROR = None
except g01_shift.DataValidationError as exc:
    G01_SHARE, G01_RANK = None, None
    G01_ERROR = str(exc)

try:
    G04_DISTANCE, G04_TRAJECTORY, G04_TWIN = g04_twins.load_data()
    G04_ERROR = None
    g04_twins.register_callbacks(app, G04_DISTANCE, G04_TRAJECTORY, G04_TWIN)
except g04_twins.DataValidationError as exc:
    G04_DISTANCE, G04_TRAJECTORY, G04_TWIN = None, None, None
    G04_ERROR = str(exc)

try:
    G05_DATA = g05_survival.load_data()
    G05_ERROR = None
    g05_survival.register_callbacks(app, G05_DATA)
except g05_survival.DataValidationError as exc:
    G05_DATA = None
    G05_ERROR = str(exc)

try:
    G06_COUNTRIES, G06_COUNTS = g06_migration_shield.load_data()
    G06_ERROR = None
    g06_migration_shield.register_callbacks(app, G06_COUNTRIES, G06_COUNTS)
except g06_migration_shield.DataValidationError as exc:
    G06_COUNTRIES, G06_COUNTS = None, None
    G06_ERROR = str(exc)


def home_layout():
    """Landing page using the original hub-* CSS classes."""
    return html.Main(
        className="hub-container",
        children=[
            html.Header(
                className="hub-header",
                children=[
                    html.Div("ANALYTICS WORKSPACE", className="hub-eyebrow"),
                    html.H1("Dashboard Hub"),
                    html.P(
                        "Choose a dashboard to explore.",
                        className="hub-intro",
                    ),
                ],
            ),
            html.Section(
                className="hub-grid",
                children=[
                    html.A(
                        href="/dashboard/g01",
                        className="hub-card",
                        children=[
                            html.Div("G01", className="hub-eyebrow"),
                            html.Div("The Great Population Shift", className="hub-card-title"),
                            html.Div(
                                "Compare regional population shares and median-age rankings through 2100.",
                                className="hub-card-description",
                            ),
                            html.Div("Open dashboard →", className="hub-card-link"),
                        ],
                    ),
                    html.A(
                        href="/dashboard/g02",
                        className="hub-card",
                        children=[
                            html.Div("G02", className="hub-eyebrow"),
                            html.Div("Global Demographic Transition", className="hub-card-title"),
                            html.Div(
                                "Explore the global distribution of demographic transition stages from 1950 to 2050.",
                                className="hub-card-description",
                            ),
                            html.Div("Open dashboard →", className="hub-card-link"),
                        ],
                    ),
                    html.A(
                        href="/dashboard/g03",
                        className="hub-card",
                        children=[
                            html.Div("G03", className="hub-eyebrow"),
                            html.Div(
                                "Demographic Cluster Transitions",
                                className="hub-card-title",
                            ),
                            html.Div(
                                "Explore demographic cluster movements from 1990 "
                                "to 2023 and the 2050 projection.",
                                className="hub-card-description",
                            ),
                            html.Div(
                                "Open dashboard →",
                                className="hub-card-link",
                            ),
                        ],
                    ),
                    html.A(
                        href="/dashboard/g04",
                        className="hub-card",
                        children=[
                            html.Div("G04", className="hub-eyebrow"),
                            html.Div("Demographic Twins", className="hub-card-title"),
                            html.Div(
                                "Compare Türkiye with similar demographic profiles across time.",
                                className="hub-card-description",
                            ),
                            html.Div("Open dashboard →", className="hub-card-link"),
                        ],
                    ),
                    html.A(
                        href="/dashboard/g05",
                        className="hub-card",
                        children=[
                            html.Div("G05", className="hub-eyebrow"),
                            html.Div("The Survival Revolution", className="hub-card-title"),
                            html.Div(
                                "Compare survival at selected ages across Türkiye's history and 2023 countries.",
                                className="hub-card-description",
                            ),
                            html.Div("Open dashboard →", className="hub-card-link"),
                        ],
                    ),
                    html.A(
                        href="/dashboard/g06",
                        className="hub-card",
                        children=[
                            html.Div("G06", className="hub-eyebrow"),
                            html.Div("The Migration Shield", className="hub-card-title"),
                            html.Div(
                                "Explore natural population change and net migration across countries over time.",
                                className="hub-card-description",
                            ),
                            html.Div("Open dashboard →", className="hub-card-link"),
                        ],
                    ),
                ],
            ),
        ],
    )


def route_layout(pathname):
    if pathname == "/dashboard/g01":
        if G01_ERROR:
            return html.Main(
                className="g01-dashboard",
                children=[
                    html.A("← Back to Dashboard Hub", href="/", className="hub-back"),
                    html.H1("G01 dashboard could not load"),
                    html.P("Check that data/out/g01_bolge_pay.csv and data/out/g01_medyan_yas_sira.csv exist and contain the expected columns."),
                    html.Pre(G01_ERROR, className="error-message"),
                ],
            )
        return g01_shift.build_layout(G01_SHARE, G01_RANK, show_back_link=True)
    if pathname == "/dashboard/g02":
        if G02_ERROR:
            return html.Main(
                className="g02-dashboard",
                children=[
                    html.A("← Back to Dashboard Hub", href="/", className="hub-back"),
                    html.H1("G02 dashboard could not load"),
                    html.P("Check that data/out/kume_atamalari.csv exists and contains the expected columns."),
                    html.Pre(G02_ERROR, className="error-message"),
                ],
            )
        return g02_map.build_layout(G02_DATA, show_back_link=True)
    if pathname == "/dashboard/g03":
        if G03_ERROR:
            return html.Main(
                className="dashboard",
                children=[
                    html.A(
                        "← Back to Dashboard Hub",
                        href="/",
                        className="hub-back",
                    ),
                    html.H1("G03 dashboard could not load"),
                    html.P(
                        "Check that the required CSV files exist and contain "
                        "the expected columns."
                    ),
                    html.Pre(G03_ERROR, className="error-message"),
                ],
            )
        # Do not wrap the G03 layout in a second .dashboard container.
        return g03_transitions.build_layout(
            G03_COUNTRIES, G03_FLOWS, G03_NOTE, show_back_link=True
        )
    if pathname == "/dashboard/g04":
        if G04_ERROR:
            return html.Main(
                className="dashboard",
                children=[
                    html.A("← Back to Dashboard Hub", href="/", className="hub-back"),
                    html.H1("G04 dashboard could not load"),
                    html.P("Check that all three required G04 CSV files exist and contain the expected columns."),
                    html.Pre(G04_ERROR, className="error-message"),
                ],
            )
        return g04_twins.build_layout(G04_DISTANCE, G04_TRAJECTORY, G04_TWIN, show_back_link=True)
    if pathname == "/dashboard/g05":
        if G05_ERROR:
            return html.Main(
                className="g05-dashboard",
                children=[
                    html.A("← Back to Dashboard Hub", href="/", className="hub-back"),
                    html.H1("G05 dashboard could not load"),
                    html.P("Check that data/out/g05_sagkalim.csv exists and contains the expected columns."),
                    html.Pre(G05_ERROR, className="error-message"),
                ],
            )
        return g05_survival.build_layout(G05_DATA, show_back_link=True)
    if pathname == "/dashboard/g06":
        if G06_ERROR:
            return html.Main(
                className="g06-dashboard",
                children=[
                    html.A("← Back to Dashboard Hub", href="/", className="hub-back"),
                    html.H1("G06 dashboard could not load"),
                    html.P("Check that data/out/g06_goc_kalkani.csv and data/out/g06_goc_kalkani_sayim.csv exist and contain the expected columns."),
                    html.Pre(G06_ERROR, className="error-message"),
                ],
            )
        return g06_migration_shield.build_layout(G06_COUNTRIES, G06_COUNTS, show_back_link=True)
    return home_layout()


app.layout = html.Div(
    [
        dcc.Location(id="hub-url", refresh=False),
        html.Div(id="hub-page-content"),
    ]
)


@app.callback(
    Output("hub-page-content", "children"),
    Input("hub-url", "pathname"),
)
def display_page(pathname):
    return route_layout(pathname)


if __name__ == "__main__":
    app.run(debug=True)
