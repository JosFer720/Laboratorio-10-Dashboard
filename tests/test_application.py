from __future__ import annotations

from pathlib import Path

from dash import Dash, dcc

from tourism_dashboard.application import create_app

DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "arrivals_migration_2009_2026.csv"
)


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
    assert [graph.id for graph in graphs] == ["arrivals-timeline", "market-chart"]


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
    outputs = [
        (output.component_id, output.component_property)
        for callback in app.callback_map.values()
        for output in callback["output"]
    ]

    assert len(app.callback_map) == 4
    assert len(outputs) == len(set(outputs))


def test_create_app_has_the_dashboard_title() -> None:
    app = create_app(DATA_PATH)
    text = " ".join(
        str(component)
        for component in _walk(app.layout)
        if isinstance(component, (str, int))
    )

    assert "Observatorio de turismo sostenible" in text
