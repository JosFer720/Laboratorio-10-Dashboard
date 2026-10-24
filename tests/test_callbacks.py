from __future__ import annotations

from pathlib import Path

import pytest

from tourism_dashboard.application import create_app
from tourism_dashboard.layout import VISUALIZATIONS

DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "arrivals_migration_2009_2026.csv"
)
MODEL_PREDICTIONS_PATH = DATA_PATH.with_name("model_predictions_s0.csv")
MODEL_METRICS_PATH = DATA_PATH.with_name("model_metrics_s0.csv")
OCCUPANCY_PATH = DATA_PATH.with_name("hotel_occupancy_inguat_2022_2024.csv")
DEFAULT_INPUTS = {
    "period-start.value": "2022-01-01",
    "period-end.value": "2024-12-01",
    "origin-filter.value": "all",
    "time-detail.value": "month",
    "v1-selection.data": None,
    "arrivals-timeline.selectedData": None,
    "arrivals-timeline.clickData": None,
    "clear-selection.n_clicks": 0,
    "main-tabs.active_tab": "arrivals",
    "model-selector.value": "lstm-catch22-contexto-w24",
    "v7-model-selection.data": {"model": "lstm-catch22-contexto-w24"},
    "market-share-chart.clickData": None,
    "market-share-back.n_clicks": 0,
    "seasonality-chart.clickData": None,
    "occupancy-chart.clickData": None,
    "clear-season-selection.n_clicks": 0,
    "seasonality-mode.value": "arrivals",
    "season-selection.data": {"period": None, "detail": "month"},
    "visible-graphs.value": [graph for graph, _, _ in VISUALIZATIONS],
    "show-all-graphs.n_clicks": 0,
    "hide-all-graphs.n_clicks": 0,
}


@pytest.fixture
def app():
    return create_app(
        DATA_PATH, MODEL_PREDICTIONS_PATH, MODEL_METRICS_PATH, OCCUPANCY_PATH
    )


def invoke(app, target, changes=None, changed=None):
    values = DEFAULT_INPUTS | (changes or {})
    key = next(key for key in app.callback_map if target in key)
    callback = app.callback_map[key]
    callback_outputs = callback["output"]
    is_multi_output = isinstance(callback_outputs, (list, tuple))
    if not is_multi_output:
        callback_outputs = [callback_outputs]
    output_spec = [
        {"id": output.component_id, "property": output.component_property}
        for output in callback_outputs
    ]
    response = app.server.test_client().post(
        "/_dash-update-component",
        json={
            "output": key,
            "outputs": output_spec if is_multi_output else output_spec[0],
            "inputs": [
                dict(item, value=values[f"{item['id']}.{item['property']}"])
                for item in callback["inputs"]
            ],
            "state": [],
            "changedPropIds": changed or [],
        },
    )
    assert response.status_code == 200, response.text
    return response.get_json()["response"]


@pytest.mark.parametrize(
    ("detail", "count"), [("month", 36), ("quarter", 12), ("year", 3)]
)
def test_timeline_callback_renders_each_detail(app, detail, count):
    result = invoke(
        app,
        "arrivals-timeline.figure",
        {"time-detail.value": detail},
        ["time-detail.value"],
    )

    assert len(result["arrivals-timeline"]["figure"]["data"][0]["y"]) == count
    assert result["arrivals-timeline"]["clickData"] is None
    assert result["arrivals-timeline"]["selectedData"] is None
    assert result["covered-months"]["children"] == "36"


def test_click_callback_exposes_selected_period(app):
    result = invoke(
        app,
        "v1-selection.data",
        {
            "arrivals-timeline.clickData": {"points": [{"customdata": ["2024-07"]}]},
        },
        ["arrivals-timeline.clickData"],
    )

    assert result["v1-selection"]["data"]["dates"] == ["2024-07-01"]
    assert result["v1-selection"]["data"]["is_selected"] is True
    assert result["clear-selection"]["disabled"] is False


def test_box_selection_takes_priority_over_simultaneous_click(app):
    result = invoke(
        app,
        "v1-selection.data",
        {
            "arrivals-timeline.selectedData": {
                "points": [{"customdata": ["2024-01"]}, {"customdata": ["2024-03"]}]
            },
            "arrivals-timeline.clickData": {"points": [{"customdata": ["2024-01"]}]},
        },
        ["arrivals-timeline.clickData", "arrivals-timeline.selectedData"],
    )

    assert result["v1-selection"]["data"]["dates"] == ["2024-01-01", "2024-03-01"]


@pytest.mark.parametrize(
    "trigger",
    [
        "period-start.value",
        "origin-filter.value",
        "time-detail.value",
        "clear-selection.n_clicks",
    ],
)
def test_global_filter_or_clear_discards_stale_graph_selection(app, trigger):
    result = invoke(
        app,
        "v1-selection.data",
        {
            "period-start.value": "2024-01-01",
            "origin-filter.value": "origin:México",
            "arrivals-timeline.selectedData": {"points": [{"customdata": ["2022-01"]}]},
            "arrivals-timeline.clickData": {"points": [{"customdata": ["2022-01"]}]},
        },
        [trigger],
    )

    selection = result["v1-selection"]["data"]
    assert len(selection["dates"]) == 12
    assert selection["market"] == "origin:México"
    assert selection["is_selected"] is False
    assert result["clear-selection"]["disabled"] is True


def test_initial_and_deselected_states_use_full_filtered_period(app):
    for changed in ([], ["arrivals-timeline.selectedData"]):
        result = invoke(app, "v1-selection.data", changed=changed)
        assert len(result["v1-selection"]["data"]["dates"]) == 36
        assert result["v1-selection"]["data"]["is_selected"] is False


def test_invalid_range_has_empty_graph_and_empty_shared_state(app):
    changes = {"period-start.value": "2024-12-01", "period-end.value": "2022-01-01"}
    timeline = invoke(app, "arrivals-timeline.figure", changes, ["period-start.value"])
    selection = invoke(app, "v1-selection.data", changes, ["period-start.value"])

    assert not timeline["arrivals-timeline"]["figure"]["data"]
    assert timeline["covered-months"]["children"] == "0"
    assert selection["v1-selection"]["data"]["dates"] == []


@pytest.mark.parametrize("tab", ["arrivals", "seasons", "models", "data"])
def test_navigation_keeps_one_panel_visible_and_disables_inapplicable_filters(app, tab):
    result = invoke(
        app,
        "arrivals-panel.hidden",
        {"main-tabs.active_tab": tab},
        ["main-tabs.active_tab"],
    )

    for panel in ("arrivals", "seasons", "models", "data"):
        assert result[f"{panel}-panel"]["hidden"] is (panel != tab)
    uses_filters = tab in {"arrivals", "seasons"}
    assert result["origin-filter"]["disabled"] is not uses_filters
    assert all(
        option["disabled"] is not uses_filters
        for option in result["time-detail"]["options"]
    )


def market_state(result):
    figure = result["market-chart"]["figure"]
    bars = figure["data"][0] if figure["data"] else None
    return figure, bars


def test_markets_follow_the_period_selected_in_the_timeline(app):
    selection = invoke(
        app,
        "v1-selection.data",
        {"arrivals-timeline.clickData": {"points": [{"customdata": ["2024-07"]}]}},
        ["arrivals-timeline.clickData"],
    )["v1-selection"]["data"]
    result = invoke(
        app, "market-chart.figure", {"v1-selection.data": selection}, ["v1-selection.data"]
    )
    _, bars = market_state(result)
    total = invoke(
        app,
        "arrivals-timeline.figure",
        {"period-start.value": "2024-07-01", "period-end.value": "2024-07-01"},
        ["period-start.value"],
    )["arrivals-total"]["children"]

    assert sum(bars["x"]) == pytest.approx(int(total.replace(".", "")), abs=len(bars["x"]))
    assert "Julio de 2024" in result["market-caption"]["children"]


def test_markets_cover_the_whole_filter_when_nothing_is_selected(app):
    full = invoke(app, "v1-selection.data")["v1-selection"]["data"]
    _, bars = market_state(
        invoke(app, "market-chart.figure", {"v1-selection.data": full})
    )

    assert len(bars["y"]) == 11
    assert bars["x"] == sorted(bars["x"], reverse=True)


def test_markets_show_a_message_when_the_selection_has_no_months(app):
    empty = {"dates": [], "market": "all", "granularity": "month", "is_selected": False}
    result = invoke(app, "market-chart.figure", {"v1-selection.data": empty})
    figure, bars = market_state(result)

    assert bars is None
    assert "No hay información" in figure["layout"]["annotations"][0]["text"]
    assert "No hay meses disponibles" in result["market-caption"]["children"]


def test_markets_tolerate_a_missing_selection(app):
    result = invoke(app, "market-chart.figure", {"v1-selection.data": None})

    assert not result["market-chart"]["figure"]["data"]


def test_model_selector_exposes_only_a_sanitized_id(app):
    valid = invoke(
        app,
        "v7-model-selection.data",
        {"model-selector.value": "prophet"},
        ["model-selector.value"],
    )
    invalid = invoke(
        app,
        "v7-model-selection.data",
        {"model-selector.value": "desconocido"},
        ["model-selector.value"],
    )

    assert valid["v7-model-selection"]["data"] == {"model": "prophet"}
    assert invalid["v7-model-selection"]["data"] == {"model": None}


def test_model_panel_updates_figure_metrics_and_status(app):
    result = invoke(
        app,
        "model-evaluation-chart.figure",
        {"v7-model-selection.data": {"model": "arima-1-1-1"}},
        ["v7-model-selection.data"],
    )

    traces = result["model-evaluation-chart"]["figure"]["data"]
    assert [trace["name"] for trace in traces] == [
        "Observado",
        "Estimado · ARIMA(1,1,1)",
    ]
    assert result["model-mae"]["children"] == "154.873"
    assert result["model-rmse"]["children"] == "169.524"
    assert result["model-mape"]["children"] == "59,3 %"
    assert "evaluación histórica" in result["model-status"]["children"]


def test_model_panel_handles_an_invalid_shared_state(app):
    result = invoke(
        app,
        "model-evaluation-chart.figure",
        {"v7-model-selection.data": {"model": "desconocido"}},
        ["v7-model-selection.data"],
    )

    assert not result["model-evaluation-chart"]["figure"]["data"]
    assert result["model-mae"]["children"] == "—"
    assert result["model-status"]["children"] == "No hay un modelo válido seleccionado."


def test_market_share_compares_regions_and_their_countries(app):
    regions = invoke(app, "market-share-chart.figure", {"time-detail.value": "year"})
    countries = invoke(
        app,
        "market-share-chart.figure",
        {"origin-filter.value": "region:América Central", "time-detail.value": "year"},
    )

    region_titles = [item["text"] for item in regions["market-share-chart"]["figure"]["layout"]["annotations"]]
    assert region_titles == [
        "América del Norte",
        "América Central",
        "América del Sur",
        "Europa",
        "Resto del mundo",
    ]
    assert regions["market-share-back"]["disabled"] is True
    assert countries["market-share-back"]["disabled"] is False
    assert countries["market-share-caption"]["children"] == "Nivel: países de América Central"


def test_market_share_explains_why_a_single_origin_has_no_comparison(app):
    result = invoke(
        app, "market-share-chart.figure", {"origin-filter.value": "origin:Belice"}
    )

    figure = result["market-share-chart"]["figure"]
    assert not figure["data"]
    assert "100 %" in figure["layout"]["annotations"][0]["text"]


def test_clicking_a_region_drills_down_and_back_returns_to_all(app):
    click = {"points": [{"customdata": ["América Central", "2024"]}]}
    drilled = invoke(
        app,
        "origin-filter.value",
        {"market-share-chart.clickData": click},
        ["market-share-chart.clickData"],
    )
    back = invoke(
        app,
        "origin-filter.value",
        {"origin-filter.value": "region:América Central", "market-share-back.n_clicks": 1},
        ["market-share-back.n_clicks"],
    )

    assert drilled["origin-filter"]["value"] == "region:América Central"
    assert drilled["market-share-chart"]["clickData"] is None
    assert back["origin-filter"]["value"] == "all"


def test_regions_without_countries_do_not_drill_down(app):
    click = {"points": [{"customdata": ["Europa", "2024"]}]}
    result = invoke(
        app,
        "origin-filter.value",
        {"market-share-chart.clickData": click},
        ["market-share-chart.clickData"],
    )

    assert "origin-filter" not in result


@pytest.mark.parametrize(
    ("source", "click"),
    [
        # El mapa de calor envía la columna y el año, sin customdata.
        ("seasonality-chart", {"points": [{"curveNumber": 0, "x": 6, "y": 2023, "z": 1.0}]}),
        ("occupancy-chart", {"points": [{"customdata": ["2023-07", "Julio de 2023"]}]}),
    ],
)
def test_clicking_either_seasonal_chart_shares_the_period(app, source, click):
    result = invoke(
        app,
        "season-selection.data",
        {f"{source}.clickData": click},
        [f"{source}.clickData"],
    )

    assert result["season-selection"]["data"] == {"period": "2023-07", "detail": "month"}
    assert result["clear-season-selection"]["disabled"] is False
    assert "Julio de 2023" in result["season-selection-label"]["children"]


def test_filter_changes_discard_the_seasonal_selection(app):
    click = {"points": [{"customdata": ["2023-07", "Julio de 2023"]}]}
    result = invoke(
        app,
        "season-selection.data",
        {"seasonality-chart.clickData": click, "time-detail.value": "quarter"},
        ["time-detail.value"],
    )

    assert result["season-selection"]["data"] == {"period": None, "detail": "quarter"}
    assert result["clear-season-selection"]["disabled"] is True


def test_selected_period_is_highlighted_in_occupancy_and_seasonality(app):
    selection = {"period": "2023-07", "detail": "month"}
    occupancy = invoke(app, "occupancy-chart.figure", {"season-selection.data": selection})
    seasonality = invoke(app, "seasonality-chart.figure", {"season-selection.data": selection})

    bars = occupancy["occupancy-chart"]["figure"]["data"][0]
    highlighted = [
        custom[0]
        for custom, color in zip(bars["customdata"], bars["marker"]["color"])
        if color == "#0B5C8E"
    ]
    assert highlighted == ["2023-07"]
    assert len(seasonality["seasonality-chart"]["figure"]["layout"]["shapes"]) == 1


def test_occupancy_explains_periods_outside_its_coverage(app):
    outside = invoke(
        app,
        "occupancy-chart.figure",
        {"period-start.value": "2010-01-01", "period-end.value": "2012-12-01"},
    )
    unpublished = invoke(
        app,
        "occupancy-chart.figure",
        {"season-selection.data": {"period": "2015-07", "detail": "month"}},
    )

    outside_figure = outside["occupancy-chart"]["figure"]
    assert not outside_figure["data"]
    assert "2022" in outside_figure["layout"]["annotations"][0]["text"]
    bars = unpublished["occupancy-chart"]["figure"]["data"][0]
    assert set(bars["marker"]["color"]) == {"#0B5C8E"}
    assert "no tiene ocupación" in unpublished["occupancy-chart"]["figure"]["layout"]["annotations"][0]["text"]


def test_yearly_detail_disables_the_share_of_year_view(app):
    result = invoke(
        app,
        "seasonality-chart.figure",
        {"time-detail.value": "year", "seasonality-mode.value": "share"},
    )

    options = {item["value"]: item["disabled"] for item in result["seasonality-mode"]["options"]}
    assert options == {"arrivals": False, "share": True}
    assert (
        result["seasonality-chart"]["figure"]["data"][0]["colorbar"]["title"]["text"]
        == "Llegadas"
    )


@pytest.mark.parametrize(
    ("detail", "count"), [("month", 36), ("quarter", 12), ("year", 3)]
)
def test_relationship_callback_uses_common_observations_and_detail(app, detail, count):
    result = invoke(
        app, "arrivals-occupancy-chart.figure", {"time-detail.value": detail}
    )
    trace = result["arrivals-occupancy-chart"]["figure"]["data"][0]

    assert len(trace["x"]) == count
    assert len(trace["y"]) == count
    assert sum(row[2] for row in trace["customdata"]) == 36


def test_relationship_origin_filter_changes_arrivals_only(app):
    full = invoke(app, "arrivals-occupancy-chart.figure")["arrivals-occupancy-chart"][
        "figure"
    ]["data"][0]
    filtered = invoke(
        app, "arrivals-occupancy-chart.figure", {"origin-filter.value": "origin:México"}
    )["arrivals-occupancy-chart"]["figure"]["data"][0]

    assert filtered["y"] == full["y"]
    assert all(country < total for country, total in zip(filtered["x"], full["x"]))


def test_occupancy_selection_highlights_the_same_period_in_relationship(app):
    selection = invoke(
        app,
        "season-selection.data",
        {
            "occupancy-chart.clickData": {"points": [{"customdata": ["2023-07"]}]},
        },
        ["occupancy-chart.clickData"],
    )["season-selection"]["data"]
    trace = invoke(
        app, "arrivals-occupancy-chart.figure", {"season-selection.data": selection}
    )["arrivals-occupancy-chart"]["figure"]["data"][0]

    selected = [
        point[0]
        for point, color in zip(trace["customdata"], trace["marker"]["color"])
        if color == "#0B5C8E"
    ]
    assert selected == ["2023-07"]
    assert len(trace["x"]) == 36


@pytest.mark.parametrize(
    "changes",
    [
        {"period-start.value": "2010-01-01", "period-end.value": "2011-12-01"},
        {"period-start.value": "2024-12-01", "period-end.value": "2022-01-01"},
        {"origin-filter.value": "origin:desconocido"},
    ],
)
def test_relationship_handles_empty_filters(app, changes):
    figure = invoke(app, "arrivals-occupancy-chart.figure", changes)[
        "arrivals-occupancy-chart"
    ]["figure"]

    assert not figure["data"]
    assert "ambas fuentes" in figure["layout"]["annotations"][0]["text"]


@pytest.mark.parametrize(
    "model_id", ["lstm-catch22-contexto-w24", "prophet", "arima-1-1-1"]
)
def test_model_selector_updates_both_evaluation_and_errors(app, model_id):
    state = invoke(
        app,
        "v7-model-selection.data",
        {"model-selector.value": model_id},
        ["model-selector.value"],
    )["v7-model-selection"]["data"]
    changes = {"v7-model-selection.data": state}
    evaluation = invoke(app, "model-evaluation-chart.figure", changes)
    errors = invoke(app, "model-errors-chart.figure", changes)
    predictions = app.server.config["TOURISM_MODEL_PREDICTIONS"]
    source = predictions.loc[predictions["model_id"] == model_id]
    trace = errors["model-errors-chart"]["figure"]["data"][0]

    assert len(trace["y"]) == 63
    assert trace["y"] == pytest.approx(
        (source["estimate"] - source["observed"]).tolist()
    )
    assert source.iloc[0]["model_label"] in trace["name"]
    assert (
        evaluation["model-status"]["children"]
        == errors["model-errors-status"]["children"]
    )
    assert trace["marker"]["color"] == "#D55E00"


@pytest.mark.parametrize("state", [None, {}, {"model": None}, {"model": "desconocido"}])
def test_model_errors_handle_invalid_selection(app, state):
    result = invoke(
        app, "model-errors-chart.figure", {"v7-model-selection.data": state}
    )
    assert not result["model-errors-chart"]["figure"]["data"]
    assert (
        result["model-errors-status"]["children"]
        == "No hay un modelo válido seleccionado."
    )


@pytest.mark.parametrize("graph_id", [graph for graph, _, _ in VISUALIZATIONS])
def test_each_graph_can_be_hidden_and_restored(app, graph_id):
    all_graphs = [graph for graph, _, _ in VISUALIZATIONS]
    hidden = invoke(
        app,
        "visible-graphs-status.children",
        {"visible-graphs.value": [graph for graph in all_graphs if graph != graph_id]},
    )
    restored = invoke(
        app, "visible-graphs-status.children", {"visible-graphs.value": all_graphs}
    )

    for graph, _, container in VISUALIZATIONS:
        assert hidden[container]["hidden"] is (graph == graph_id)
        assert restored[container]["hidden"] is False
    assert hidden["visible-graphs-status"]["children"] == "7 de 8 seleccionadas"


@pytest.mark.parametrize("value", [[], None, ["desconocido", None, {}]])
def test_no_visible_graphs_has_clear_status_and_no_store_changes(app, value):
    result = invoke(
        app, "visible-graphs-status.children", {"visible-graphs.value": value}
    )
    assert all(result[container]["hidden"] for _, _, container in VISUALIZATIONS)
    assert "Ninguna seleccionada" in result["visible-graphs-status"]["children"]
    assert not {
        "v1-selection",
        "season-selection",
        "v7-model-selection",
        "model-selector",
        "origin-filter",
    }.intersection(result)


def test_show_all_and_hide_all_buttons(app):
    hidden = invoke(
        app,
        "visible-graphs.value",
        {"hide-all-graphs.n_clicks": 1},
        ["hide-all-graphs.n_clicks"],
    )
    shown = invoke(
        app,
        "visible-graphs.value",
        {"show-all-graphs.n_clicks": 1},
        ["show-all-graphs.n_clicks"],
    )
    assert hidden["visible-graphs"]["value"] == []
    assert shown["visible-graphs"]["value"] == [graph for graph, _, _ in VISUALIZATIONS]


def test_hidden_charts_keep_responding_to_shared_model_and_filters(app):
    invoke(app, "visible-graphs-status.children", {"visible-graphs.value": []})
    state = invoke(
        app,
        "v7-model-selection.data",
        {"model-selector.value": "prophet"},
        ["model-selector.value"],
    )["v7-model-selection"]["data"]
    errors = invoke(
        app, "model-errors-chart.figure", {"v7-model-selection.data": state}
    )
    timeline = invoke(
        app,
        "arrivals-timeline.figure",
        {"period-start.value": "2024-07-01", "period-end.value": "2024-07-01"},
    )
    restored = invoke(app, "visible-graphs-status.children")
    assert (
        errors["model-errors-chart"]["figure"]["data"][0]["name"] == "Error · Prophet"
    )
    assert len(timeline["arrivals-timeline"]["figure"]["data"][0]["x"]) == 1
    assert all(
        restored[container]["hidden"] is False for _, _, container in VISUALIZATIONS
    )
