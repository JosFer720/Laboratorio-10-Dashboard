from pathlib import Path

import pandas as pd
import pytest

from tourism_dashboard.data import load_arrivals, load_occupancy
from tourism_dashboard.exploration import arrivals_occupancy, filter_arrivals
from tourism_dashboard.figures import arrivals_occupancy_figure

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture
def sources():
    return load_arrivals(DATA_DIR / "arrivals_migration_2009_2026.csv"), load_occupancy(
        DATA_DIR / "hotel_occupancy_inguat_2022_2024.csv"
    )


def test_relationship_uses_only_common_months_and_real_totals(sources):
    arrivals, occupancy = sources
    rows = arrivals_occupancy(
        arrivals, occupancy, "2009-01-01", "2026-06-01", "all", "month"
    )
    raw = pd.read_csv(DATA_DIR / "arrivals_migration_2009_2026.csv")
    expected = raw.loc[
        raw["date"].between("2022-01-01", "2024-12-01"), "reported_total"
    ]

    assert len(rows) == 36
    assert rows["arrivals"].tolist() == pytest.approx(expected.tolist())
    assert rows["occupancy_rate"].tolist() == pytest.approx(
        occupancy["occupancy_rate"].tolist()
    )
    assert rows["date"].min() == pd.Timestamp("2022-01-01")
    assert rows["date"].max() == pd.Timestamp("2024-12-01")


@pytest.mark.parametrize("detail", ["month", "quarter", "year"])
def test_same_common_months_are_used_for_both_aggregates(sources, detail):
    arrivals, occupancy = sources
    hotels = occupancy.loc[occupancy["date"] != "2022-02-01"]
    rows = arrivals_occupancy(
        arrivals, hotels, "2022-01-01", "2022-03-01", "all", detail
    )
    expected = arrivals.loc[
        arrivals["date"].isin(pd.to_datetime(["2022-01-01", "2022-03-01"]))
    ]
    selected_hotels = hotels.loc[hotels["date"].between("2022-01-01", "2022-03-01")]

    assert rows["months"].sum() == 2
    assert rows["arrivals"].sum() == pytest.approx(expected["arrivals"].sum())
    assert rows["rooms_occupied"].sum() == selected_hotels["rooms_occupied"].sum()
    assert rows["rooms_available"].sum() == selected_hotels["rooms_available"].sum()
    for row in rows.itertuples():
        assert row.occupancy_rate == pytest.approx(
            row.rooms_occupied / row.rooms_available * 100
        )


def test_market_filter_does_not_change_national_occupancy(sources):
    arrivals, occupancy = sources
    rows = arrivals_occupancy(
        arrivals,
        occupancy,
        "2022-01-01",
        "2024-12-01",
        "region:América Central",
        "year",
    )
    filtered = filter_arrivals(
        arrivals, "2022-01-01", "2024-12-01", "region:América Central"
    )
    assert rows["arrivals"].sum() == pytest.approx(filtered["arrivals"].sum())
    for row in rows.itertuples():
        yearly = occupancy.loc[occupancy["year"] == row.date.year]
        assert row.occupancy_rate == pytest.approx(
            yearly["rooms_occupied"].sum() / yearly["rooms_available"].sum() * 100
        )


def test_empty_occupancy_has_no_invented_values(sources):
    arrivals, occupancy = sources
    rows = arrivals_occupancy(
        arrivals, occupancy.iloc[:0], "2022-01-01", "2024-12-01", "all", "month"
    )
    figure = arrivals_occupancy_figure(rows, "month", None)
    assert rows.empty
    assert not figure.data
    assert "2022 y 2024" in figure.layout.annotations[0].text


def test_relationship_does_not_modify_sources(sources):
    arrivals, occupancy = sources
    before_arrivals, before_occupancy = (
        arrivals.copy(deep=True),
        occupancy.copy(deep=True),
    )
    rows = arrivals_occupancy(
        arrivals, occupancy, "2022-01-01", "2024-12-01", "all", "month"
    )
    figure = arrivals_occupancy_figure(rows, "month", "2023-07")
    assert len(figure.data) == 1
    assert figure.data[0].mode == "markers"
    pd.testing.assert_frame_equal(arrivals, before_arrivals)
    pd.testing.assert_frame_equal(occupancy, before_occupancy)
