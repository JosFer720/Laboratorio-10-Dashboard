from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.synthetic import apply_problem, build_migration, build_mobility
from tourism_pipeline.validation import (
    ControlStatus,
    MethodologyContext,
    QualityControlError,
    Severity,
    run_quality_controls,
    validate_columns_and_types,
    validate_dates_and_coverage,
    validate_methodology,
    validate_missing_values,
    validate_uniqueness,
    validate_values_and_denominators,
)


@pytest.fixture
def config(tmp_path: Path):
    return load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.fixture
def sources() -> tuple[pd.DataFrame, pd.DataFrame]:
    mobility = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in build_mobility().items()],
        ignore_index=True,
    )
    return mobility, build_migration()


def _problem_sources(problem: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    mobility, migration = apply_problem(build_mobility(), build_migration(), problem)
    combined = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in mobility.items()],
        ignore_index=True,
    )
    return combined, migration


def test_columns_and_types_pass_warn_and_stop(config, sources):
    mobility, migration = sources
    healthy = validate_columns_and_types(mobility, migration, config)
    warning = validate_columns_and_types(
        mobility.assign(columna_adicional="dato"), migration, config
    )
    broken_mobility, broken_migration = _problem_sources("missing_column")
    failed = validate_columns_and_types(broken_mobility, broken_migration, config)

    assert healthy.status is ControlStatus.PASSED
    assert warning.status is ControlStatus.WARNING
    assert failed.status is ControlStatus.FAILED
    assert failed.severity is Severity.CRITICAL


def test_dates_and_coverage_warn_for_expected_gap_and_stop_for_invalid_date(config, sources):
    mobility, migration = sources
    warning = validate_dates_and_coverage(mobility, migration, config)
    invalid_mobility, invalid_migration = _problem_sources("invalid_date")
    failed = validate_dates_and_coverage(invalid_mobility, invalid_migration, config)

    assert warning.status is ControlStatus.WARNING
    assert warning.detail["expected_gaps"] == ["2026-01", "2026-02"]
    assert failed.status is ControlStatus.FAILED
    assert "invalid" in failed.detail


def test_dates_and_coverage_stops_when_a_fit_month_is_missing(config, sources):
    mobility, migration = sources
    mobility = mobility.loc[mobility["fecha"] != pd.Timestamp("2025-12-01")]

    result = validate_dates_and_coverage(mobility, migration, config)

    assert result.status is ControlStatus.FAILED
    assert result.detail["missing_required_mobility"] == ["2025-12"]


def test_dates_and_coverage_stops_without_migration_for_an_estimate_month(config, sources):
    mobility, migration = sources
    migration = migration.loc[
        ~((migration["Año"] == 2026) & (migration["Mes cod"].isin([1, 2])))
    ]

    result = validate_dates_and_coverage(mobility, migration, config)

    assert result.status is ControlStatus.FAILED
    assert result.detail["missing_required_migration"] == ["2026-01", "2026-02"]


def test_uniqueness_passes_and_detects_injected_duplicate(config, sources):
    mobility, migration = sources
    healthy = validate_uniqueness(mobility, migration, config)
    duplicate_mobility, duplicate_migration = _problem_sources("duplicate_row")
    failed = validate_uniqueness(duplicate_mobility, duplicate_migration, config)

    assert healthy.status is ControlStatus.PASSED
    assert failed.status is ControlStatus.FAILED
    assert failed.detail["mobility_duplicate_rows"] == 2


def test_uniqueness_warns_for_duplicate_outside_configured_migration_window(config, sources):
    mobility, migration = sources
    old = migration.iloc[[0]].assign(**{"Año": 2022})
    migration = pd.concat([migration, old, old], ignore_index=True)

    result = validate_uniqueness(mobility, migration, config)

    assert result.status is ControlStatus.WARNING
    assert result.detail["ignored_migration_duplicate_rows"] == 1


def test_missing_values_pass_warn_and_stop(config, sources):
    mobility, migration = sources
    healthy = validate_missing_values(mobility, migration, config)
    optional_missing = migration.copy()
    optional_missing.loc[0, "Región dos"] = np.nan
    warning = validate_missing_values(mobility, optional_missing, config)
    broken_mobility, broken_migration = _problem_sources("missing_values")
    failed = validate_missing_values(broken_mobility, broken_migration, config)

    assert healthy.status is ControlStatus.PASSED
    assert warning.status is ControlStatus.WARNING
    assert failed.status is ControlStatus.FAILED
    assert failed.detail["required_missing"]["mobility.visitantes"] == 5


def test_values_and_denominators_pass_warn_and_stop(config, sources):
    mobility, migration = sources
    healthy = validate_values_and_denominators(mobility, migration, config)
    with_zero = mobility.copy()
    with_zero.loc[0, "visitantes"] = 0.0
    warning = validate_values_and_denominators(with_zero, migration, config)
    broken_mobility, broken_migration = _problem_sources("zero_denominator")
    failed = validate_values_and_denominators(broken_mobility, broken_migration, config)

    assert healthy.status is ControlStatus.PASSED
    assert warning.status is ControlStatus.WARNING
    assert failed.status is ControlStatus.FAILED
    assert failed.detail["invalid_denominator_periods"] == ["2025-12"]


def test_values_and_denominators_reject_negative_and_non_finite(config, sources):
    mobility, migration = sources
    mobility.loc[0, "visitantes"] = -1
    migration.loc[0, "Viajero"] = np.inf

    result = validate_values_and_denominators(mobility, migration, config)

    assert result.status is ControlStatus.FAILED
    assert result.detail["negative_counts"]
    assert result.detail["non_finite_counts"]


def test_methodology_pass_warn_and_stop(config, sources):
    mobility, migration = sources
    healthy = validate_methodology(mobility, migration, config, MethodologyContext())
    unexpected = mobility.copy()
    unexpected.loc[0, "fecha"] = pd.Timestamp("2026-09-01")
    warning = validate_methodology(
        unexpected,
        migration,
        config,
        MethodologyContext(),
    )
    failed = validate_methodology(
        mobility,
        migration,
        config,
        MethodologyContext(mobility_source="daily"),
    )

    assert healthy.status is ControlStatus.PASSED
    assert warning.status is ControlStatus.WARNING
    assert failed.status is ControlStatus.FAILED
    assert "monthly mobility source" in failed.detail["violations"]


def test_methodology_rejects_totals_and_zero_filled_uncovered_months(config, sources):
    mobility, migration = sources
    total = mobility.copy()
    total.loc[0, ["destino", "fecha", "visitantes"]] = [
        "Total",
        pd.Timestamp("2026-01-01"),
        0,
    ]

    result = validate_methodology(
        total,
        migration,
        config,
        MethodologyContext(aggregates_subdestinations=True),
    )

    assert result.status is ControlStatus.FAILED
    assert "subdestination aggregation" in result.detail["violations"]
    assert "zero-filled uncovered periods" in result.detail["violations"]
    assert "total rows" in result.detail["violations"]


def test_runner_writes_report_and_raises_after_critical_failure(config, tmp_path):
    mobility, migration = _problem_sources("missing_column")
    report_path = tmp_path / "quality-report.json"

    with pytest.raises(QualityControlError) as error:
        run_quality_controls(
            mobility,
            migration,
            config,
            report_path,
            run_id="run-1",
            generated_at=datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc),
        )

    assert error.value.report.has_critical_failures
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-1"
    assert len(payload["controls"]) == 6
    assert all("warning_condition" in item and "stop_condition" in item for item in payload["controls"])


@pytest.mark.parametrize(
    ("source", "column"),
    [("mobility", "fecha"), ("migration", "Año")],
)
def test_runner_still_writes_report_when_a_structural_column_is_missing(
    config, sources, tmp_path, source: str, column: str
):
    mobility, migration = sources
    if source == "mobility":
        mobility = mobility.drop(columns=column)
    else:
        migration = migration.drop(columns=column)
    report_path = tmp_path / f"{source}-missing.json"

    with pytest.raises(QualityControlError):
        run_quality_controls(
            mobility, migration, config, report_path, run_id=f"missing-{source}"
        )

    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8"))["has_critical_failures"]


def test_runner_returns_report_when_there_are_only_warnings(config, sources, tmp_path):
    mobility, migration = sources
    report = run_quality_controls(
        mobility,
        migration,
        config,
        tmp_path / "quality-report.json",
        run_id="run-2",
    )

    assert not report.has_critical_failures
    assert {result.name for result in report.results} == {
        "columns_and_types",
        "dates_and_coverage",
        "uniqueness",
        "missing_values",
        "values_and_denominators",
        "methodology",
    }
