
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output

df = pd.read_csv("./data/out/g02_kume_harita.csv")

cluster_colors = {
    "1": "#2166AC",
    "2": "#67A9CF",
    "3": "#F7F7F7",
    "4": "#EF8A62",
    "5": "#B2182B",
}

cluster_order = ["5", "4", "3", "2", "1"]


def create_map(selected_year):
    dff = df.copy()

    if selected_year == 1950:
        dff["selected_cluster"] = dff["cluster_1990"]
    else:
        dff["selected_cluster"] = dff["cluster_2023"]

    dff["selected_cluster"] = (
        dff["selected_cluster"].fillna("Bilinmiyor").astype(str)
    )

    colors = {
        **cluster_colors,
        "Bilinmiyor": "#D1D5DB",
    }

    fig = px.choropleth(
        dff,
        locations="iso3",
        locationmode="ISO-3",
        color="selected_cluster",
        color_discrete_map=colors,
        category_orders={
            "selected_cluster": cluster_order + ["Bilinmiyor"]
        },
        hover_name="country",
        hover_data={
            "iso3": True,
            "cluster_1990": True,
            "cluster_2023": True,
            "selected_cluster": True,
        },
        labels={
            "selected_cluster": "Cluster",
            "cluster_1990": "Cluster (1950)",
            "cluster_2023": "Cluster (2023)",
            "iso3": "ISO-3",
        },
        projection="natural earth",
    )

    fig.update_layout(
        title=f"Dünya Cluster Haritası — {selected_year}",
        template="plotly_white",
        height=700,
        margin=dict(l=0, r=0, t=60, b=0),
        legend_title_text="Cluster",
        legend=dict(
            traceorder="normal",
        ),
        geo=dict(
            showframe=False,
            showcountries=True,
            countrycolor="white",
            projection_type="natural earth",
        ),
    )

    return fig


app = Dash(__name__)

button_style = {
    "padding": "10px 24px",
    "fontSize": "16px",
    "border": "1px solid #CBD5E1",
    "borderRadius": "8px",
    "cursor": "pointer",
    "backgroundColor": "white",
}

app.layout = html.Div(
    style={
        "maxWidth": "1400px",
        "margin": "auto",
        "padding": "20px",
        "fontFamily": "Arial",
    },
    children=[
        html.H1("Global Cluster Dashboard"),

        html.Div(
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "12px",
                "marginBottom": "20px",
            },
            children=[
                html.Label(
                    "Yıl seç:",
                    style={"fontWeight": "bold"},
                ),
                html.Button(
                    "1950",
                    id="year-1950",
                    n_clicks=0,
                    style=button_style,
                ),
                html.Button(
                    "2023",
                    id="year-2023",
                    n_clicks=0,
                    style=button_style,
                ),
                dcc.Store(id="selected-year", data=1950),
            ],
        ),

        dcc.Graph(id="world-map"),
    ],
)


@app.callback(
    Output("selected-year", "data"),
    Input("year-1950", "n_clicks"),
    Input("year-2023", "n_clicks"),
    prevent_initial_call=True,
)
def select_year(click_1950, click_2023):
    from dash import ctx

    if ctx.triggered_id == "year-1950":
        return 1950
    elif ctx.triggered_id == "year-2023":
        return 2023

    return 1950


@app.callback(
    Output("world-map", "figure"),
    Input("selected-year", "data"),
)
def update_map(selected_year):
    return create_map(selected_year)


if __name__ == "__main__":
    app.run(debug=True)
