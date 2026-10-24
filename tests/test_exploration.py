from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tourism_dashboard.callbacks import summary_values
from tourism_dashboard.data import load_arrivals, load_occupancy
from tourism_dashboard.exploration import (
    aggregate_arrivals,
    aggregate_markets,
    aggregate_occupancy,
    apply_selection,
    filter_arrivals,
    filter_market,
    heatmap_event,
    make_season_selection,
    make_selection,
    market_options,
    market_share,
    month_options,
    seasonal_cells,
)
from tourism_dashboard.figures import arrivals_figure

DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "arrivals_migration_2009_2026.csv"
)


@pytest.fixture
def arrivals():
    return load_arrivals(DATA_PATH)


@pytest.mark.parametrize(
    ("detail", "count"), [("month", 210), ("quarter", 70), ("year", 18)]
)
def test_aggregation_preserves_real_totals(arrivals, detail, count):
    grouped = aggregate_arrivals(arrivals, detail)

    assert len(grouped) == count
    assert grouped["arrivals"].sum() == pytest.approx(arrivals["arrivals"].sum())
    assert grouped["months"].sum() == 210
    assert grouped["date"].is_monotonic_increasing


def test_regional_filter_sums_countries_without_double_counting(arrivals):
    filtered = filter_arrivals(
        arrivals, "2024-01-01", "2024-03-01", "region:América del Norte"
    )
    raw = pd.read_csv(DATA_PATH)
    expected = (
        raw.loc[
            raw["date"].between("2024-01-01", "2024-03-01"),
            ["canada", "united_states", "mexico"],
        ]
        .sum()
        .sum()
    )

    assert filtered["arrivals"].sum() == pytest.approx(expected)
    assert set(filtered["origin"]) == {"Canadá", "Estados Unidos", "México"}


def test_partial_quarters_include_only_filtered_months(arrivals):
    filtered = filter_arrivals(
        arrivals, "2024-02-01", "2024-03-01", "origin:El Salvador"
    )
    grouped = aggregate_arrivals(filtered, "quarter")

    assert len(grouped) == 1
    assert grouped.iloc[0]["months"] == 2
    assert grouped.iloc[0]["arrivals"] == filtered["arrivals"].sum()


@pytest.mark.parametrize(
    ("start", "end", "market"),
    [
        ("2024-12-01", "2022-01-01", "all"),
        ("2030-01-01", "2030-12-01", "all"),
        (None, "2024-12-01", "all"),
        ("invalid", "2024-12-01", "all"),
        ("2022-01-01", "2024-12-01", None),
        ("2022-01-01", "2024-12-01", "country:inventado"),
        ("2022-01-01", "2024-12-01", "origin:inventado"),
    ],
)
def test_empty_or_invalid_filters_return_no_rows(arrivals, start, end, market):
    assert filter_arrivals(arrivals, start, end, market).empty


def test_filter_options_come_from_observed_months_and_origin_types(arrivals):
    months = month_options(arrivals)
    options = market_options(arrivals)
    labels = {option["value"]: option["label"] for option in options}

    assert len(months) == 210
    assert months[0] == {"value": "2009-01-01", "label": "Enero de 2009"}
    assert months[-1]["value"] == "2026-06-01"
    assert len(labels) == len(options)
    assert labels["origin:Europa"].endswith("agregado")
    assert labels["origin:Canadá"].endswith("país")
    assert labels["origin:Guatemala"].endswith("país")
    assert "region:América Central" in labels


@pytest.mark.parametrize(
    ("detail", "keys", "count"),
    [
        ("month", ["2024-01", "2024-03"], 2),
        ("quarter", ["2024Q2"], 3),
        ("year", ["2023"], 12),
    ],
)
def test_selection_retains_exact_months_for_each_detail(arrivals, detail, keys, count):
    event = {"points": [{"customdata": [key]} for key in keys]}
    selection = make_selection(arrivals, "all", detail, event)
    rows = apply_selection(arrivals, selection)

    assert selection["is_selected"] is True
    assert len(selection["dates"]) == count
    assert rows["date"].nunique() == count
    if detail == "month":
        assert selection["dates"] == ["2024-01-01", "2024-03-01"]
        assert not (rows["date"] == "2024-02-01").any()


def test_selection_is_clipped_to_global_period_and_market(arrivals):
    filtered = filter_arrivals(arrivals, "2024-02-01", "2024-03-01", "origin:México")
    selection = make_selection(
        filtered, "origin:México", "quarter", {"points": [{"customdata": ["2024Q1"]}]}
    )
    rows = apply_selection(arrivals, selection)

    assert selection["dates"] == ["2024-02-01", "2024-03-01"]
    assert set(rows["origin"]) == {"México"}
    assert len(rows) == 2


@pytest.mark.parametrize(
    "event",
    [
        None,
        {},
        {"points": []},
        {"points": None},
        {"points": [None, {}, {"customdata": None}, {"customdata": [None]}]},
        {"points": [{"customdata": ["2030-01"]}]},
        {"points": [{"customdata": ["2024Q1"]}]},
    ],
)
def test_missing_empty_or_stale_selection_restores_filtered_period(arrivals, event):
    selection = make_selection(arrivals, "all", "month", event)

    assert selection["is_selected"] is False
    assert len(selection["dates"]) == 210


def test_empty_data_has_valid_selection_and_clear_message(arrivals):
    empty = arrivals.iloc[:0]
    selection = make_selection(empty, "all", "month")
    figure = arrivals_figure(empty, "month", "empty")

    assert selection["dates"] == []
    assert apply_selection(arrivals, selection).empty
    assert not figure.data
    assert "No hay información" in figure.layout.annotations[0].text
    assert summary_values(empty) == ("—", "—", "Sin información en este periodo", "0")


@pytest.mark.parametrize(
    "selection",
    [None, {}, {"dates": None}, {"dates": [None, {}, "invalid"], "market": "all"}],
)
def test_invalid_shared_state_is_safe_to_consume(arrivals, selection):
    assert apply_selection(arrivals, selection).empty


def test_missing_months_are_gaps_and_never_zero(arrivals):
    filtered = arrivals.loc[
        arrivals["date"].isin(pd.to_datetime(["2024-01-01", "2024-03-01"]))
    ]
    figure = arrivals_figure(filtered, "month", "gap")

    assert len(figure.data[0].y) == 3
    assert figure.data[0].y[1] is None
    assert figure.data[0].connectgaps is False


def test_arrivals_figure_preserves_fractional_observations(arrivals):
    filtered = arrivals.loc[arrivals["date"] == "2009-01-01"]
    expected = filtered["arrivals"].sum()

    figure = arrivals_figure(filtered, "month", "fractional")

    assert figure.data[0].y[0] == pytest.approx(expected)
    assert figure.data[0].y[0] != int(expected)


def test_data_integrity_after_filter_aggregation_and_selection(arrivals):
    original = arrivals.copy(deep=True)
    filtered = filter_arrivals(
        arrivals, "2024-01-01", "2024-12-01", "region:América Central"
    )
    arrivals_figure(filtered, "year", "integrity")
    apply_selection(
        arrivals, make_selection(filtered, "region:América Central", "year")
    )

    pd.testing.assert_frame_equal(arrivals, original)


def test_market_aggregation_keeps_the_selected_total_and_shares(arrivals):
    selection = make_selection(arrivals, "region:América Central", "month")
    rows = apply_selection(arrivals, selection)
    markets = aggregate_markets(rows)

    assert markets["arrivals"].sum() == pytest.approx(rows["arrivals"].sum())
    assert markets["share"].sum() == pytest.approx(100)
    assert markets["arrivals"].is_monotonic_decreasing
    assert aggregate_markets(arrivals.iloc[:0]).empty


OCCUPANCY_PATH = DATA_PATH.with_name("hotel_occupancy_inguat_2022_2024.csv")


@pytest.mark.parametrize(("detail", "columns"), [("month", 12), ("quarter", 4)])
def test_seasonal_cells_share_adds_to_one_hundred_per_year(arrivals, detail, columns):
    cells = seasonal_cells(arrivals, detail)

    assert cells["subperiod"].max() == columns
    assert cells.groupby("year")["share"].sum().round(6).eq(100).all()
    assert cells["arrivals"].sum() == pytest.approx(arrivals["arrivals"].sum())


def test_seasonal_cells_leave_months_without_data_out(arrivals):
    cells = seasonal_cells(arrivals, "month")

    assert len(cells.loc[cells["year"] == 2026]) == 6
    assert cells["period_key"].is_unique


def test_market_share_uses_regions_then_countries(arrivals):
    regions = market_share(arrivals, "all", "year")
    central = filter_market(arrivals, "region:América Central")
    countries = market_share(central, "region:América Central", "year")

    assert regions["group"].nunique() == 5
    assert regions.groupby("period_key")["share"].sum().round(6).eq(100).all()
    assert set(countries["group"]) == set(central["origin"])
    assert countries.groupby("period_key")["share"].sum().round(6).eq(100).all()
    assert market_share(arrivals, "origin:Belice", "year").empty


def test_occupancy_aggregation_divides_room_totals():
    occupancy = load_occupancy(OCCUPANCY_PATH)
    quarters = aggregate_occupancy(occupancy, "2009-01-01", "2026-06-01", "quarter")
    first = occupancy.loc[occupancy["date"] < "2022-04-01"]

    assert len(quarters) == 12
    assert quarters.iloc[0]["occupancy_rate"] == pytest.approx(
        first["rooms_occupied"].sum() / first["rooms_available"].sum() * 100
    )
    assert aggregate_occupancy(occupancy, "2010-01-01", "2012-12-01", "month").empty


@pytest.mark.parametrize(
    ("event", "detail", "expected"),
    [
        ({"points": [{"customdata": ["2023Q3"]}]}, "quarter", "2023Q3"),
        ({"points": [{"customdata": ["2023-07"]}]}, "quarter", None),
        ({"points": [{"customdata": [""]}]}, "month", None),
        ({"points": "invalido"}, "month", None),
        (None, "year", None),
    ],
)
def test_season_selection_only_accepts_keys_of_the_current_detail(event, detail, expected):
    assert make_season_selection(event, detail) == {"period": expected, "detail": detail}


@pytest.mark.parametrize(
    ("detail", "expected"), [("month", "2023-07"), ("quarter", "2023Q7"), ("year", "2023")]
)
def test_heatmap_clicks_become_period_keys(detail, expected):
    event = heatmap_event({"points": [{"x": 6, "y": 2023}]}, detail)

    assert event == {"points": [{"customdata": [expected]}]}
    # Una clave imposible, como el trimestre 7, no llega al estado compartido.
    assert make_season_selection(event, detail)["period"] == (
        None if detail == "quarter" else expected
    )
