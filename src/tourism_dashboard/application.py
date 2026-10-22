from __future__ import annotations

from pathlib import Path

from dash import Dash

from tourism_dashboard.callbacks import register_callbacks
from tourism_dashboard.data import load_arrivals
from tourism_dashboard.layout import build_layout


def create_app(data_path: str | Path) -> Dash:
    arrivals = load_arrivals(data_path)
    app = Dash(
        __name__,
        assets_folder=str(Path(__file__).resolve().parent / "assets"),
        title="Observatorio de turismo sostenible",
        update_title="Actualizando…",
    )
    app.index_string = app.index_string.replace("<html>", '<html lang="es">')
    app.server.config["TOURISM_DATA"] = arrivals
    app.layout = build_layout(arrivals)
    register_callbacks(app, arrivals)
    return app
