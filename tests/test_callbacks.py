from __future__ import annotations

from pathlib import Path

import pytest

from tourism_dashboard.application import create_app

DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "arrivals_inguat_2022_2024.csv"
)
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
}


@pytest.fixture
def app():
    return create_app(DATA_PATH)


def invoke(app, target, changes=None, changed=None):
    values = DEFAULT_INPUTS | (changes or {})
    key = next(key for key in app.callback_map if target in key)
    callback = app.callback_map[key]
    response = app.server.test_client().post(
        "/_dash-update-component",
        json={
            "output": key,
            "outputs": [
                {"id": output.component_id, "property": output.component_property}
                for output in callback["output"]
            ],
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
            "origin-filter.value": "origin:Mexico",
            "arrivals-timeline.selectedData": {"points": [{"customdata": ["2022-01"]}]},
            "arrivals-timeline.clickData": {"points": [{"customdata": ["2022-01"]}]},
        },
        [trigger],
    )

    selection = result["v1-selection"]["data"]
    assert len(selection["dates"]) == 12
    assert selection["market"] == "origin:Mexico"
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
    assert result["origin-filter"]["disabled"] is (tab != "arrivals")
    assert all(
        option["disabled"] is (tab != "arrivals")
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

    assert sum(bars["x"]) == int(total.replace(".", ""))
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
