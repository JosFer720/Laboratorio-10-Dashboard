from __future__ import annotations

from pathlib import Path

from dash import Dash, dcc

from tourism_dashboard.application import create_app


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "arrivals_inguat_2022_2024.csv"


def _walk(component: object):
    yield component
    children = getattr(component, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            yield from _walk(child)
    elif children is not None:
        yield from _walk(children)


def test_create_app_loads_data_without_adding_graphs() -> None:
    app = create_app(DATA_PATH)

    assert isinstance(app, Dash)
    assert len(app.server.config["TOURISM_DATA"]) == 396
    assert not any(isinstance(component, dcc.Graph) for component in _walk(app.layout))


def test_create_app_has_the_dashboard_title() -> None:
    app = create_app(DATA_PATH)
    text = " ".join(
        str(component)
        for component in _walk(app.layout)
        if isinstance(component, (str, int))
    )

    assert "Observatorio de turismo sostenible" in text
