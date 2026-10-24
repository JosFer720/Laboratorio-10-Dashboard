from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from dash import Dash, dcc

from tourism_dashboard.application import create_app
from tourism_dashboard.data import TourismDataError

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "arrivals_migration_2009_2026.csv"
)
MODEL_PREDICTIONS_PATH = DATA_PATH.with_name("model_predictions_s0.csv")
MODEL_METRICS_PATH = DATA_PATH.with_name("model_metrics_s0.csv")
OCCUPANCY_PATH = DATA_PATH.with_name("hotel_occupancy_inguat_2022_2024.csv")
GRAPH_IDS = [
    "arrivals-timeline",
    "market-chart",
    "market-share-chart",
    "seasonality-chart",
    "occupancy-chart",
    "arrivals-occupancy-chart",
    "model-evaluation-chart",
    "model-errors-chart",
]


def _walk(component: object):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None:
        yield from _walk(children)


def test_create_app_loads_data_and_mounts_timeline_and_markets() -> None:
    app = create_app(DATA_PATH)

    assert isinstance(app, Dash)
    assert len(app.server.config["TOURISM_DATA"]) == 2_310
    graphs = [
        component for component in _walk(app.layout) if isinstance(component, dcc.Graph)
    ]
    assert [graph.id for graph in graphs] == GRAPH_IDS


def test_create_app_exposes_validated_model_data() -> None:
    app = create_app(DATA_PATH, MODEL_PREDICTIONS_PATH, MODEL_METRICS_PATH)

    predictions = app.server.config["TOURISM_MODEL_PREDICTIONS"]
    metrics = app.server.config["TOURISM_MODEL_METRICS"]
    assert len(predictions) == 189
    assert len(metrics) == 3
    assert set(predictions["model_id"]) == set(metrics["model_id"])

    graphs = [
        component for component in _walk(app.layout) if isinstance(component, dcc.Graph)
    ]
    assert [graph.id for graph in graphs] == GRAPH_IDS
    stores = [
        component for component in _walk(app.layout) if isinstance(component, dcc.Store)
    ]
    model_store = next(store for store in stores if store.id == "v7-model-selection")
    assert model_store.data == {"model": "lstm-catch22-contexto-w24"}


def test_comparison_displays_all_original_metrics_and_a_single_model_selector():
    app = create_app(DATA_PATH, MODEL_PREDICTIONS_PATH, MODEL_METRICS_PATH)
    components = list(_walk(app.layout))
    table = next(
        component
        for component in components
        if getattr(component, "id", None) == "model-comparison-table"
    )
    body = table.children[2]
    assert [row.children[0].children for row in body.children] == [
        "LSTM catch22 (ventana 24)",
        "Prophet",
        "ARIMA(1,1,1)",
    ]
    assert [[cell.children for cell in row.children[1:]] for row in body.children] == [
        ["55.256,39", "67.734,70", "29,16"],
        ["132.304,36", "139.548,64", "60,89"],
        ["154.872,62", "169.524,19", "59,30"],
    ]
    source = app.server.config["TOURISM_MODEL_METRICS"]
    for actual, expected in zip(body.children, source.to_dict("records")):
        assert [cell.title for cell in actual.children[1:]] == [
            str(expected[key]) for key in ("mae", "rmse", "mape")
        ]
    assert (
        sum(
            isinstance(component, dcc.Dropdown) and component.id == "model-selector"
            for component in components
        )
        == 1
    )


def test_graph_selection_mounts_all_eight_graphs_without_replacing_shared_stores():
    app = create_app(DATA_PATH)
    components = list(_walk(app.layout))
    selector = next(
        component
        for component in components
        if getattr(component, "id", None) == "visible-graphs"
    )
    assert set(selector.value) == set(GRAPH_IDS)
    assert len(selector.options) == 8
    assert {
        component.id for component in components if isinstance(component, dcc.Store)
    } == {"v1-selection", "v7-model-selection", "season-selection"}


def test_create_app_keeps_single_path_call_compatible() -> None:
    app = create_app(DATA_PATH)

    assert app.server.config["TOURISM_MODEL_PREDICTIONS"].empty
    assert app.server.config["TOURISM_MODEL_METRICS"].empty


def test_create_app_loads_optional_hotel_occupancy() -> None:
    without_occupancy = create_app(DATA_PATH)
    with_occupancy = create_app(DATA_PATH, occupancy_path=OCCUPANCY_PATH)

    assert without_occupancy.server.config["TOURISM_OCCUPANCY"].empty
    assert len(with_occupancy.server.config["TOURISM_OCCUPANCY"]) == 36


def test_create_app_rejects_only_one_model_artifact_path() -> None:
    with pytest.raises(ValueError, match="ambas rutas"):
        create_app(DATA_PATH, MODEL_PREDICTIONS_PATH)


def test_create_app_rejects_model_observations_that_do_not_match_arrivals(
    tmp_path: Path,
) -> None:
    predictions = pd.read_csv(MODEL_PREDICTIONS_PATH)
    first_date = predictions.loc[0, "date"]
    predictions.loc[predictions["date"] == first_date, "observed"] += 1
    predictions_path = tmp_path / "predictions.csv"
    predictions.to_csv(predictions_path, index=False)

    with pytest.raises(TourismDataError, match="serie de llegadas"):
        create_app(DATA_PATH, predictions_path, MODEL_METRICS_PATH)


def test_create_app_rejects_metrics_that_do_not_match_predictions(
    tmp_path: Path,
) -> None:
    metrics = pd.read_csv(MODEL_METRICS_PATH)
    metrics.loc[0, "mae"] += 1
    metrics_path = tmp_path / "metrics.csv"
    metrics.to_csv(metrics_path, index=False)

    with pytest.raises(TourismDataError, match="recalculadas"):
        create_app(DATA_PATH, MODEL_PREDICTIONS_PATH, metrics_path)


def test_layout_has_unique_component_ids_and_shared_selection() -> None:
    app = create_app(DATA_PATH)
    ids = [
        component.id
        for component in _walk(app.layout)
        if getattr(component, "id", None)
    ]
    stores = [
        component for component in _walk(app.layout) if isinstance(component, dcc.Store)
    ]

    assert len(ids) == len(set(ids))
    selection = next(store for store in stores if store.id == "v1-selection").data
    assert selection["is_selected"] is False
    assert len(selection["dates"]) == 210
    assert selection["market"] == "all"


def test_app_serves_layout_dependencies_and_local_styles() -> None:
    app = create_app(DATA_PATH)
    client = app.server.test_client()

    page = client.get("/")
    assert page.status_code == 200
    assert '<html lang="es">' in page.text
    assert "cdn.jsdelivr.net" not in page.text
    assert client.get("/_dash-layout").status_code == 200
    assert client.get("/_dash-dependencies").status_code == 200
    assert client.get("/assets/styles.css").status_code == 200
    assert client.get("/assets/00_bootstrap.min.css").status_code == 200
    locale = client.get("/assets/01_plotly-locale-es.js")
    assert locale.status_code == 200
    assert b"PlotlyLocales" in locale.data
    font = client.get("/assets/fonts/InterVariable.woff2")
    assert font.status_code == 200
    assert font.data[:4] == b"wOF2"


def test_callbacks_have_unique_outputs() -> None:
    app = create_app(DATA_PATH)
    outputs = []
    for callback in app.callback_map.values():
        callback_outputs = callback["output"]
        if not isinstance(callback_outputs, (list, tuple)):
            callback_outputs = [callback_outputs]
        outputs.extend(
            (output.component_id, output.component_property)
            for output in callback_outputs
        )

    assert len(app.callback_map) == 15
    assert len(outputs) == len(set(outputs))


def test_create_app_has_the_dashboard_title() -> None:
    app = create_app(DATA_PATH)
    text = " ".join(
        str(component)
        for component in _walk(app.layout)
        if isinstance(component, (str, int))
    )

    assert "Observatorio de turismo sostenible" in text
    assert "predicciones evaluadas históricamente" in text
    assert "No se muestra intervalo" in text
    assert "visitantes no residentes" not in text
    assert "cruceristas" not in text.lower()
