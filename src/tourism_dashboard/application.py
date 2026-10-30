from __future__ import annotations

from pathlib import Path

import pandas as pd
from dash import Dash

from tourism_dashboard.callbacks import register_callbacks
from tourism_dashboard.data import (
    MODEL_METRIC_COLUMNS,
    MODEL_PREDICTION_COLUMNS,
    OCCUPANCY_COLUMNS,
    load_arrivals,
    load_model_metrics,
    load_model_predictions,
    load_occupancy,
    validate_model_results,
)
from tourism_dashboard.layout import build_layout
from tourism_dashboard.approved import approved_panel, register_approved_callbacks, versions_path


def create_app(
    data_path: str | Path,
    model_predictions_path: str | Path | None = None,
    model_metrics_path: str | Path | None = None,
    occupancy_path: str | Path | None = None,
    approved_versions_path: str | Path | None = None,
) -> Dash:
    arrivals = load_arrivals(data_path)
    if (model_predictions_path is None) != (model_metrics_path is None):
        raise ValueError("Se deben proporcionar ambas rutas de modelos.")
    if model_predictions_path is None:
        model_predictions = pd.DataFrame(columns=MODEL_PREDICTION_COLUMNS)
        model_metrics = pd.DataFrame(columns=MODEL_METRIC_COLUMNS)
    else:
        model_predictions = load_model_predictions(model_predictions_path)
        model_metrics = load_model_metrics(model_metrics_path)
    validate_model_results(arrivals, model_predictions, model_metrics)
    if occupancy_path is None:
        occupancy = pd.DataFrame(columns=OCCUPANCY_COLUMNS)
    else:
        occupancy = load_occupancy(occupancy_path)
    app = Dash(
        __name__,
        assets_folder=str(Path(__file__).resolve().parent / "assets"),
        title="Observatorio de turismo sostenible",
        update_title="Actualizando…",
    )
    app.index_string = app.index_string.replace("<html>", '<html lang="es">')
    app.server.config["TOURISM_DATA"] = arrivals
    app.server.config["TOURISM_MODEL_PREDICTIONS"] = model_predictions
    app.server.config["TOURISM_MODEL_METRICS"] = model_metrics
    app.server.config["TOURISM_OCCUPANCY"] = occupancy
    app.layout = build_layout(arrivals, model_predictions, model_metrics, occupancy)
    content = next(child for child in app.layout.children if getattr(child, "id", None) == "dashboard-content")
    content.children.insert(0, approved_panel())
    register_approved_callbacks(app, approved_versions_path or versions_path())
    register_callbacks(app, arrivals, model_predictions, model_metrics, occupancy)
    return app
