from __future__ import annotations

from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, html

from tourism_dashboard.data import load_arrivals


def create_app(data_path: str | Path) -> Dash:
    arrivals = load_arrivals(data_path)
    app = Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        title="Observatorio de turismo sostenible",
    )
    app.server.config["TOURISM_DATA"] = arrivals
    app.layout = dbc.Container(
        [
            html.H1("Observatorio de turismo sostenible"),
            html.P("Tablero interactivo de indicadores turisticos de Guatemala."),
        ],
        fluid=True,
    )
    return app
