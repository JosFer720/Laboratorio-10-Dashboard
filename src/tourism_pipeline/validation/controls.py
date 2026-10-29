from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.validation.models import (
    ControlResult,
    ControlStatus,
    MethodologyContext,
    QualityControlError,
    QualityReport,
    Severity,
    utc_now,
)


def _result(
    name: str,
    description: str,
    status: ControlStatus,
    message: str,
    detail: dict[str, Any],
    warning_condition: str,
    stop_condition: str,
) -> ControlResult:
    severity = Severity.CRITICAL if status is ControlStatus.FAILED else Severity.WARNING
    return ControlResult(
        name=name,
        description=description,
        status=status,
        severity=severity,
        message=message,
        detail=detail,
        warning_condition=warning_condition,
        stop_condition=stop_condition,
    )


def validate_columns_and_types(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> ControlResult:
    quality = config.quality
    expected_mobility = set(quality.mobility_columns) | {SHEET_COLUMN}
    expected_migration = set(quality.migration_columns)
    missing = {
        "mobility": sorted(expected_mobility - set(mobility.columns)),
        "migration": sorted(expected_migration - set(migration.columns)),
    }
    unexpected = {
        "mobility": sorted(set(mobility.columns) - expected_mobility),
        "migration": sorted(set(migration.columns) - expected_migration),
    }
    incompatible: list[str] = []
    for source, frame, columns in (
        ("mobility", mobility, quality.mobility_numeric_columns),
        ("migration", migration, quality.migration_numeric_columns),
    ):
        for column in columns:
            if column in frame and pd.to_numeric(frame[column], errors="coerce").isna().sum() > frame[column].isna().sum():
                incompatible.append(f"{source}.{column}")
    if "fecha" in mobility:
        parsed = pd.to_datetime(mobility["fecha"], errors="coerce", format="mixed")
        if parsed.isna().sum() > mobility["fecha"].isna().sum():
            incompatible.append("mobility.fecha")

    detail = {"missing": missing, "incompatible": incompatible, "unexpected": unexpected}
    if any(missing.values()) or incompatible:
        return _result(
            "columns_and_types", "Required columns and compatible source types", ControlStatus.FAILED,
            "Missing required columns or incompatible values were found.", detail,
            "Unexpected extra columns are present.",
            "A required column is absent or a required type is incompatible.",
        )
    if any(unexpected.values()):
        return _result(
            "columns_and_types", "Required columns and compatible source types", ControlStatus.WARNING,
            "The required structure is valid, with extra columns.", detail,
            "Unexpected extra columns are present.",
            "A required column is absent or a required type is incompatible.",
        )
    return _result(
        "columns_and_types", "Required columns and compatible source types", ControlStatus.PASSED,
        "All required columns and types are valid.", detail,
        "Unexpected extra columns are present.",
        "A required column is absent or a required type is incompatible.",
    )


def _migration_periods(migration: pd.DataFrame) -> pd.Series:
    if not {"Año", "Mes cod"} <= set(migration.columns):
        return pd.Series(pd.NaT, index=migration.index, dtype="datetime64[ns]")
    years = pd.to_numeric(migration["Año"], errors="coerce")
    months = pd.to_numeric(migration["Mes cod"], errors="coerce")
    return pd.to_datetime(
        pd.DataFrame({"year": years, "month": months, "day": 1}), errors="coerce"
    )


def validate_dates_and_coverage(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> ControlResult:
    mobility_dates = (
        pd.to_datetime(mobility["fecha"], errors="coerce", format="mixed")
        if "fecha" in mobility
        else pd.Series(pd.NaT, index=mobility.index, dtype="datetime64[ns]")
    )
    migration_dates = _migration_periods(migration)
    invalid = {
        "mobility": int(mobility_dates.isna().sum()),
        "migration": int(migration_dates.isna().sum()),
    }
    observed_mobility = set(mobility_dates.dropna().dt.to_period("M").dt.to_timestamp())
    selected_travelers = (
        migration["Tipo de Viajero"].isin(config.parameters.migration.traveler_types)
        if "Tipo de Viajero" in migration
        else pd.Series(False, index=migration.index)
    )
    observed_migration = set(
        migration_dates.loc[selected_travelers].dropna().dt.to_period("M").dt.to_timestamp()
    )
    fit_periods = set(config.periods.fit)
    required_migration = fit_periods | set(config.periods.estimate)
    missing_required_mobility = sorted(fit_periods - observed_mobility)
    missing_required_migration = sorted(required_migration - observed_migration)
    expected_gaps = sorted(set(config.periods.estimate) - observed_mobility)
    detail = {
        "invalid": invalid,
        "missing_required_mobility": [f"{value:%Y-%m}" for value in missing_required_mobility],
        "missing_required_migration": [f"{value:%Y-%m}" for value in missing_required_migration],
        "expected_gaps": [f"{value:%Y-%m}" for value in expected_gaps],
    }
    if any(invalid.values()) or missing_required_mobility or missing_required_migration:
        return _result(
            "dates_and_coverage", "Valid dates and coverage required for fitting and estimation", ControlStatus.FAILED,
            "Invalid dates or missing required fit periods were found.", detail,
            "Configured uncovered mobility periods are absent and remain unfilled.",
            "A date is invalid or a period required for fitting is missing.",
        )
    if expected_gaps:
        return _result(
            "dates_and_coverage", "Valid dates and coverage required for fitting and estimation", ControlStatus.WARNING,
            "Expected mobility gaps are present and were not filled with zero.", detail,
            "Configured uncovered mobility periods are absent and remain unfilled.",
            "A date is invalid or a period required for fitting is missing.",
        )
    return _result(
        "dates_and_coverage", "Valid dates and coverage required for fitting and estimation", ControlStatus.PASSED,
        "Dates and required coverage are valid.", detail,
        "Configured uncovered mobility periods are absent and remain unfilled.",
        "A date is invalid or a period required for fitting is missing.",
    )


def validate_uniqueness(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> ControlResult:
    quality = config.quality
    mobility_key = [column for column in quality.mobility_key if column in mobility]
    migration_key = [column for column in quality.migration_key if column in migration]
    missing_keys = {
        "mobility": sorted(set(quality.mobility_key) - set(mobility_key)),
        "migration": sorted(set(quality.migration_key) - set(migration_key)),
    }
    mobility_duplicates = int(mobility.duplicated(mobility_key, keep="first").sum()) if mobility_key else 0
    years = (
        pd.to_numeric(migration["Año"], errors="coerce")
        if "Año" in migration
        else pd.Series(np.nan, index=migration.index)
    )
    active = years >= config.parameters.migration.first_year
    migration_duplicates = (
        int(migration.loc[active].duplicated(migration_key, keep="first").sum()) if migration_key else 0
    )
    ignored_duplicates = (
        int(migration.loc[~active].duplicated(migration_key, keep="first").sum()) if migration_key else 0
    )
    detail = {
        "missing_key_columns": missing_keys,
        "mobility_duplicate_rows": mobility_duplicates,
        "migration_duplicate_rows": migration_duplicates,
        "ignored_migration_duplicate_rows": ignored_duplicates,
    }
    if any(missing_keys.values()) or mobility_duplicates or migration_duplicates:
        return _result(
            "uniqueness", "Unique rows at each source's declared granularity", ControlStatus.FAILED,
            "Duplicate rows or an incomplete uniqueness key were found.", detail,
            "Duplicates only occur before the configured migration methodology window.",
            "Duplicates occur in mobility or in the migration window used by the pipeline.",
        )
    if ignored_duplicates:
        return _result(
            "uniqueness", "Unique rows at each source's declared granularity", ControlStatus.WARNING,
            "Duplicates exist only outside the configured migration window.", detail,
            "Duplicates only occur before the configured migration methodology window.",
            "Duplicates occur in mobility or in the migration window used by the pipeline.",
        )
    return _result(
        "uniqueness", "Unique rows at each source's declared granularity", ControlStatus.PASSED,
        "No duplicate source rows were found.", detail,
        "Duplicates only occur before the configured migration methodology window.",
        "Duplicates occur in mobility or in the migration window used by the pipeline.",
    )


def validate_missing_values(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> ControlResult:
    quality = config.quality
    required_missing: dict[str, int] = {}
    for source, frame, columns in (
        ("mobility", mobility, quality.required_non_null_mobility),
        ("migration", migration, quality.required_non_null_migration),
    ):
        for column in columns:
            count = len(frame) if column not in frame else int(frame[column].isna().sum())
            if count:
                required_missing[f"{source}.{column}"] = count
    optional_missing: dict[str, int] = {}
    optional_fraction = 0.0
    for column in quality.optional_migration_columns:
        if column in migration:
            count = int(migration[column].isna().sum())
            if count:
                optional_missing[f"migration.{column}"] = count
    if len(migration) and quality.optional_migration_columns:
        optional_fraction = sum(optional_missing.values()) / (
            len(migration) * len(quality.optional_migration_columns)
        )
    detail = {
        "required_missing": required_missing,
        "optional_missing": optional_missing,
        "optional_missing_fraction": optional_fraction,
        "max_optional_missing_fraction": quality.max_optional_missing_fraction,
    }
    if required_missing or optional_fraction > quality.max_optional_missing_fraction:
        return _result(
            "missing_values", "Missing values distinguished by modeling impact", ControlStatus.FAILED,
            "Missing values prevent estimation or exceed the configured optional-data threshold.", detail,
            "Optional descriptive values are missing within the configured threshold.",
            "A required modeling value is missing or optional missingness exceeds the threshold.",
        )
    if optional_missing:
        return _result(
            "missing_values", "Missing values distinguished by modeling impact", ControlStatus.WARNING,
            "Only optional descriptive values are missing.", detail,
            "Optional descriptive values are missing within the configured threshold.",
            "A required modeling value is missing or optional missingness exceeds the threshold.",
        )
    return _result(
        "missing_values", "Missing values distinguished by modeling impact", ControlStatus.PASSED,
        "No cell-level missing values affect the pipeline.", detail,
        "Optional descriptive values are missing within the configured threshold.",
        "A required modeling value is missing or optional missingness exceeds the threshold.",
    )


def validate_values_and_denominators(
    mobility: pd.DataFrame, migration: pd.DataFrame, config: PipelineConfig
) -> ControlResult:
    numeric_fields = {
        "mobility.visitantes": mobility.get("visitantes"),
        "mobility.dias_persona": mobility.get("dias_persona"),
        "mobility.permanencia_prom": mobility.get("permanencia_prom"),
        "migration.Viajero": migration.get("Viajero"),
    }
    negative_counts: dict[str, int] = {}
    non_finite_counts: dict[str, int] = {}
    zero_counts: dict[str, int] = {}
    for name, values in numeric_fields.items():
        if values is None:
            non_finite_counts[name] = 1
            continue
        numeric = pd.to_numeric(values, errors="coerce")
        finite = pd.Series(np.isfinite(numeric), index=numeric.index)
        if (~finite & numeric.notna()).any() or numeric.isna().sum() > values.isna().sum():
            non_finite_counts[name] = int((~finite | numeric.isna()).sum())
        if (numeric < 0).any():
            negative_counts[name] = int((numeric < 0).sum())
        if (numeric == 0).any():
            zero_counts[name] = int((numeric == 0).sum())

    invalid_denominators: list[str] = []
    needed = {"Año", "Mes cod", "Tipo de Viajero", "Viajero"}
    if needed <= set(migration.columns):
        periods = _migration_periods(migration)
        selected = migration["Tipo de Viajero"].isin(config.parameters.migration.traveler_types)
        totals = pd.to_numeric(migration.loc[selected, "Viajero"], errors="coerce").groupby(periods[selected]).sum(min_count=1)
        invalid_denominators = [
            f"{period:%Y-%m}" for period in config.periods.fit
            if period not in totals.index or not math.isfinite(float(totals.loc[period])) or totals.loc[period] <= 0
        ]
    else:
        invalid_denominators = [f"{period:%Y-%m}" for period in config.periods.fit]
    detail = {
        "negative_counts": negative_counts,
        "non_finite_counts": non_finite_counts,
        "zero_counts": zero_counts,
        "invalid_denominator_periods": invalid_denominators,
    }
    if negative_counts or non_finite_counts or invalid_denominators:
        return _result(
            "values_and_denominators", "Finite non-negative counts and positive national denominators", ControlStatus.FAILED,
            "Negative, non-finite, or invalid denominator values were found.", detail,
            "Zero counts are present but no fitting denominator is zero.",
            "A count is negative/non-finite or a national fitting denominator is not positive.",
        )
    row_count = max(len(mobility) + len(migration), 1)
    zero_fraction = sum(zero_counts.values()) / row_count
    if zero_fraction > config.quality.zero_count_warning_fraction:
        return _result(
            "values_and_denominators", "Finite non-negative counts and positive national denominators", ControlStatus.WARNING,
            "Zero counts were found without invalidating a fitting denominator.", detail,
            "Zero counts are present but no fitting denominator is zero.",
            "A count is negative/non-finite or a national fitting denominator is not positive.",
        )
    return _result(
        "values_and_denominators", "Finite non-negative counts and positive national denominators", ControlStatus.PASSED,
        "Counts and fitting denominators are valid.", detail,
        "Zero counts are present but no fitting denominator is zero.",
        "A count is negative/non-finite or a national fitting denominator is not positive.",
    )


def validate_methodology(
    mobility: pd.DataFrame,
    migration: pd.DataFrame,
    config: PipelineConfig,
    context: MethodologyContext,
) -> ControlResult:
    del migration
    violations: list[str] = []
    if context.mobility_source != "monthly":
        violations.append("monthly mobility source")
    if context.aggregates_subdestinations:
        violations.append("subdestination aggregation")
    if "destino" in mobility and mobility["destino"].astype(str).str.fullmatch(
        r"\s*total\s*", case=False, na=False
    ).any():
        violations.append("total rows")
    dates = (
        pd.to_datetime(mobility["fecha"], errors="coerce", format="mixed")
        if "fecha" in mobility
        else pd.Series(pd.NaT, index=mobility.index, dtype="datetime64[ns]")
    )
    uncovered = dates.dt.to_period("M").dt.to_timestamp().isin(config.periods.estimate)
    if uncovered.any():
        values = pd.to_numeric(mobility.loc[uncovered, "visitantes"], errors="coerce") if "visitantes" in mobility else pd.Series(dtype=float)
        if values.empty or (values.fillna(0) == 0).any():
            violations.append("zero-filled uncovered periods")
        else:
            violations.append("observed rows in configured uncovered periods")
    configured = set(config.periods.mobility_coverage) | set(config.periods.estimate)
    observed = set(dates.dropna().dt.to_period("M").dt.to_timestamp())
    unexpected = sorted(observed - configured)
    detail = {
        "violations": violations,
        "unexpected_periods": [f"{period:%Y-%m}" for period in unexpected],
        "mobility_source": context.mobility_source,
        "aggregates_subdestinations": context.aggregates_subdestinations,
    }
    if violations:
        return _result(
            "methodology", "Monthly-source, subdestination-level, non-zero-fill methodology", ControlStatus.FAILED,
            "One or more methodological rules were violated.", detail,
            "Mobility contains periods outside the configured coverage window.",
            "Daily data is used, subdestinations are aggregated, totals are constructed, or gaps are zero-filled.",
        )
    if unexpected:
        return _result(
            "methodology", "Monthly-source, subdestination-level, non-zero-fill methodology", ControlStatus.WARNING,
            "The methodology is valid, but mobility has unexpected periods.", detail,
            "Mobility contains periods outside the configured coverage window.",
            "Daily data is used, subdestinations are aggregated, totals are constructed, or gaps are zero-filled.",
        )
    return _result(
        "methodology", "Monthly-source, subdestination-level, non-zero-fill methodology", ControlStatus.PASSED,
        "The automated methodological rules are satisfied.", detail,
        "Mobility contains periods outside the configured coverage window.",
        "Daily data is used, subdestinations are aggregated, totals are constructed, or gaps are zero-filled.",
    )


def run_quality_controls(
    mobility: pd.DataFrame,
    migration: pd.DataFrame,
    config: PipelineConfig,
    report_path: str | Path,
    run_id: str,
    generated_at: datetime | None = None,
    methodology: MethodologyContext | None = None,
) -> QualityReport:
    methodology = methodology or MethodologyContext()
    results = (
        validate_columns_and_types(mobility, migration, config),
        validate_dates_and_coverage(mobility, migration, config),
        validate_uniqueness(mobility, migration, config),
        validate_missing_values(mobility, migration, config),
        validate_values_and_denominators(mobility, migration, config),
        validate_methodology(mobility, migration, config, methodology),
    )
    path = Path(report_path)
    report = QualityReport(run_id, generated_at or utc_now(), results, path)
    payload = {
        "run_id": report.run_id,
        "generated_at": report.generated_at.isoformat(timespec="seconds"),
        "has_critical_failures": report.has_critical_failures,
        "controls": [result.as_record() for result in report.results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if report.has_critical_failures:
        raise QualityControlError(report)
    return report
