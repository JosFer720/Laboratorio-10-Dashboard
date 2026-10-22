from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tourism_dashboard.data import (
    CANONICAL_COLUMNS,
    MODEL_METRIC_COLUMNS,
    MODEL_PREDICTION_COLUMNS,
    OCCUPANCY_COLUMNS,
    TourismDataError,
    load_arrivals,
    load_model_metrics,
    load_model_predictions,
    load_occupancy,
)


DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "arrivals_migration_2009_2026.csv"
)


def test_load_arrivals_returns_canonical_tidy_data() -> None:
    result = load_arrivals(DATA_PATH)

    assert tuple(result.columns) == CANONICAL_COLUMNS
    assert len(result) == 2_310
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result["arrivals"].dtype == "Float64"
    assert result["destination_zone"].unique().tolist() == ["Guatemala"]
    assert set(result["origin_level"]) == {"country", "region"}
    assert result["date"].nunique() == 210
    assert result["date"].min() == pd.Timestamp("2009-01-01")
    assert result["date"].max() == pd.Timestamp("2026-06-01")


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        ("2009-01-01", 149_944.02934517286),
        ("2022-01-01", 134_303.0),
        ("2026-06-01", 245_687.58097737003),
    ],
)
def test_load_arrivals_preserves_reported_monthly_totals(
    date: str, expected: int
) -> None:
    result = load_arrivals(DATA_PATH)

    monthly_total = result.loc[result["date"] == date, "arrivals"].sum()

    assert monthly_total == pytest.approx(expected, abs=1e-6)


def test_load_arrivals_derives_calendar_fields() -> None:
    result = load_arrivals(DATA_PATH)
    april = result.loc[result["date"] == "2024-04-01"].iloc[0]

    assert april["year"] == 2024
    assert april["quarter"] == 2
    assert april["month"] == 4
    assert april["month_name"] == "Abril"


def test_load_arrivals_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "incomplete.csv"
    path.write_text("date,canada\n2024-01-01,10\n", encoding="utf-8")

    with pytest.raises(TourismDataError, match="columnas requeridas"):
        load_arrivals(path)


def test_load_arrivals_rejects_negative_values(tmp_path: Path) -> None:
    source = pd.read_csv(DATA_PATH).head(1)
    source.loc[0, "canada"] = -1
    path = tmp_path / "negative.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match="negativos"):
        load_arrivals(path)


def test_load_arrivals_preserves_the_expected_origin_categories() -> None:
    result = load_arrivals(DATA_PATH)

    assert result["origin"].drop_duplicates().tolist() == [
        "Canadá",
        "Estados Unidos",
        "México",
        "Belice",
        "El Salvador",
        "Honduras",
        "Resto de América Central",
        "América del Sur",
        "Europa",
        "Resto del mundo",
        "Guatemala",
    ]


def test_load_arrivals_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(TourismDataError, match="No se encontro"):
        load_arrivals(tmp_path / "missing.csv")


def test_load_arrivals_rejects_large_difference_from_reported_total(
    tmp_path: Path,
) -> None:
    source = pd.read_csv(DATA_PATH).head(1)
    source.loc[0, "reported_total"] += 2
    path = tmp_path / "inconsistent.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match="total mensual"):
        load_arrivals(path)


OCCUPANCY_PATH = DATA_PATH.with_name("hotel_occupancy_inguat_2022_2024.csv")
MODEL_PREDICTIONS_PATH = DATA_PATH.with_name("model_predictions_s0.csv")
MODEL_METRICS_PATH = DATA_PATH.with_name("model_metrics_s0.csv")
MODEL_IDS = {
    "lstm-catch22-contexto-w24",
    "prophet",
    "arima-1-1-1",
}


def test_load_occupancy_returns_monthly_series() -> None:
    result = load_occupancy(OCCUPANCY_PATH)

    assert tuple(result.columns) == OCCUPANCY_COLUMNS
    assert len(result) == 36
    assert result["date"].is_monotonic_increasing
    assert result["rooms_available"].dtype == "Int64"


@pytest.mark.parametrize(
    ("year", "available", "occupied"),
    [
        (2022, 9_142_615, 4_586_817),
        (2023, 9_367_587, 5_760_943),
        (2024, 9_453_493, 6_819_342),
    ],
)
def test_load_occupancy_preserves_reported_annual_totals(
    year: int, available: int, occupied: int
) -> None:
    result = load_occupancy(OCCUPANCY_PATH)
    annual = result.loc[result["year"] == year]

    assert annual["rooms_available"].sum() == available
    assert annual["rooms_occupied"].sum() == occupied


def test_load_occupancy_rate_matches_reported_percentages() -> None:
    result = load_occupancy(OCCUPANCY_PATH)

    assert (
        result["occupancy_rate"].round().astype("Int64")
        == result["reported_occupancy_pct"]
    ).all()


def test_load_occupancy_rejects_more_occupied_than_available(
    tmp_path: Path,
) -> None:
    source = pd.read_csv(OCCUPANCY_PATH).head(1)
    source.loc[0, "rooms_occupied"] = source.loc[0, "rooms_available"] + 1
    path = tmp_path / "overbooked.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match="superan"):
        load_occupancy(path)


def test_load_model_predictions_returns_complete_common_holdout() -> None:
    result = load_model_predictions(MODEL_PREDICTIONS_PATH)

    assert tuple(result.columns) == MODEL_PREDICTION_COLUMNS
    assert len(result) == 189
    assert set(result["model_id"]) == MODEL_IDS
    assert result.groupby("model_id").size().eq(63).all()
    assert result["date"].min() == pd.Timestamp("2021-04-01")
    assert result["date"].max() == pd.Timestamp("2026-06-01")
    assert result.groupby("date")["observed"].nunique().eq(1).all()


def test_load_model_predictions_rejects_different_observed_values(
    tmp_path: Path,
) -> None:
    source = pd.read_csv(MODEL_PREDICTIONS_PATH)
    source.loc[source["model_id"] == "prophet", "observed"] += 1
    path = tmp_path / "different-observed.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match="observados"):
        load_model_predictions(path)


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("date", "2021-04-02", "meses"),
        ("estimate", float("inf"), "finitos"),
        ("estimate", -1, "negativos"),
    ],
)
def test_load_model_predictions_rejects_invalid_values(
    tmp_path: Path, column: str, value: object, message: str
) -> None:
    source = pd.read_csv(MODEL_PREDICTIONS_PATH)
    source.loc[0, column] = value
    path = tmp_path / "invalid-predictions.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match=message):
        load_model_predictions(path)


def test_load_model_predictions_rejects_incomplete_model(tmp_path: Path) -> None:
    source = pd.read_csv(MODEL_PREDICTIONS_PATH).iloc[1:]
    path = tmp_path / "incomplete-predictions.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match="63"):
        load_model_predictions(path)


def test_load_model_metrics_returns_one_row_per_model() -> None:
    result = load_model_metrics(MODEL_METRICS_PATH)

    assert tuple(result.columns) == MODEL_METRIC_COLUMNS
    assert len(result) == 3
    assert set(result["model_id"]) == MODEL_IDS
    assert result["model_id"].is_unique
    assert result["train_end"].eq(pd.Timestamp("2021-03-01")).all()
    assert result["evaluation_start"].eq(pd.Timestamp("2021-04-01")).all()
    assert result["evaluation_end"].eq(pd.Timestamp("2026-06-01")).all()
    assert result.loc[result["model_id"] == "arima-1-1-1", "aic"].notna().all()
    assert result.loc[result["model_id"] != "arima-1-1-1", "aic"].isna().all()


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("rmse", float("nan"), "finitas"),
        ("mape", -1, "negativas"),
        ("evaluation_end", "2026-05-01", "evaluacion"),
        ("source_commit", "f2155dcc", "commit"),
        ("source_commit", "0" * 40, "procedencia"),
    ],
)
def test_load_model_metrics_rejects_invalid_contract(
    tmp_path: Path, column: str, value: object, message: str
) -> None:
    source = pd.read_csv(MODEL_METRICS_PATH)
    source.loc[0, column] = value
    path = tmp_path / "invalid-metrics.csv"
    source.to_csv(path, index=False)

    with pytest.raises(TourismDataError, match=message):
        load_model_metrics(path)
