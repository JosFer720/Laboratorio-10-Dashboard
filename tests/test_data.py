from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tourism_dashboard.data import (
    CANONICAL_COLUMNS,
    TourismDataError,
    load_arrivals,
)


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "arrivals_inguat_2022_2024.csv"


def test_load_arrivals_returns_canonical_tidy_data() -> None:
    result = load_arrivals(DATA_PATH)

    assert tuple(result.columns) == CANONICAL_COLUMNS
    assert len(result) == 396
    assert pd.api.types.is_datetime64_any_dtype(result["date"])
    assert result["arrivals"].dtype == "Int64"
    assert result["destination_zone"].unique().tolist() == ["Guatemala"]
    assert set(result["origin_level"]) == {"country", "region", "segment"}


@pytest.mark.parametrize(
    ("date", "expected"),
    [("2022-01-01", 78_285), ("2023-01-01", 217_869), ("2024-12-01", 322_849)],
)
def test_load_arrivals_preserves_reported_monthly_totals(
    date: str, expected: int
) -> None:
    result = load_arrivals(DATA_PATH)

    monthly_total = result.loc[result["date"] == date, "arrivals"].sum()

    assert monthly_total == expected


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
