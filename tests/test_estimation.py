from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.estimation import (
    RESULT_COLUMNS,
    estimate_uncovered_months,
    new_run_id,
    write_outputs,
)
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.preparation import prepare
from tourism_pipeline.synthetic import MOBILITY_STRUCTURE, build_migration, build_mobility

GENERATED_AT = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def config(tmp_path: Path):
    return load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.fixture
def prepared(config):
    mobility = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in build_mobility().items()],
        ignore_index=True,
    )
    return prepare(mobility, build_migration(), config)


def test_estimates_cover_january_and_february_for_every_subdestination(config, prepared):
    outputs = estimate_uncovered_months(prepared, config, "run-1", GENERATED_AT)
    results = outputs.results
    subdestinations = sum(len(items) for items in MOBILITY_STRUCTURE.values())

    assert tuple(results.columns) == RESULT_COLUMNS
    assert len(results) == subdestinations * 2
    assert set(results["period"]) == {pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01")}
    assert set(results["kind"]) == {"estimate"}
    assert set(results["unit"]) == {"visitantes únicos del mes"}
    assert set(results["run_id"]) == {"run-1"}
    assert set(results["procedure_version"]) == {"1"}
    assert (results["value"] > 0).all()


def test_estimate_is_factor_times_national_entries(config, prepared):
    outputs = estimate_uncovered_months(prepared, config, "run-1", GENERATED_AT)

    entries = prepared.entries.set_index("period")["entries"]
    factor = outputs.factors.loc[
        (outputs.factors["destination"] == "Livingston")
        & (outputs.factors["target_period"] == "2026-02-01"),
        "factor",
    ].item()
    value = outputs.results.loc[
        (outputs.results["destination"] == "Livingston")
        & (outputs.results["period"] == "2026-02-01"),
        "value",
    ].item()
    assert value == pytest.approx(factor * entries[pd.Timestamp("2026-02-01")])


def test_month_without_national_entries_stays_out_instead_of_zero(config, prepared):
    entries = prepared.entries.loc[prepared.entries["period"] != "2026-02-01"]
    partial = type(prepared)(prepared.visitors, entries, prepared.coverage)

    results = estimate_uncovered_months(partial, config, "run-1", GENERATED_AT).results

    assert set(results["period"]) == {pd.Timestamp("2026-01-01")}


def test_national_series_records_the_months_used(config, prepared):
    series = estimate_uncovered_months(prepared, config, "run-1", GENERATED_AT).national_series

    uses = series.set_index("period")["use"]
    assert uses[pd.Timestamp("2025-09-01")] == "ajuste"
    assert uses[pd.Timestamp("2026-01-01")] == "estimación"
    assert len(series) == 10


def test_outputs_are_written_with_dates_and_no_zeros(config, prepared, tmp_path):
    outputs = estimate_uncovered_months(prepared, config, "run-1", GENERATED_AT)

    written = write_outputs(outputs, tmp_path / "salida", config)

    assert {path.name for path in written.values()} == {
        "estimates.csv",
        "reparto_factors.csv",
        "national_entries.csv",
        "coverage.csv",
    }
    results = pd.read_csv(written["results"])
    assert results["period"].tolist()[0] == "2026-01-01"
    assert results["generated_at"].iloc[0] == "2026-10-29T12:00:00+00:00"
    assert (results["value"] > 0).all()


def test_run_ids_are_unique_and_start_with_the_time():
    first = new_run_id(GENERATED_AT)
    second = new_run_id(GENERATED_AT)

    assert first.startswith("20261029T120000Z-")
    assert first != second
