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
            "columns_and_types", "Columnas indispensables y tipos compatibles en las fuentes", ControlStatus.FAILED,
            "Falta una columna indispensable o hay valores de un tipo incompatible.", detail,
            "Hay columnas adicionales no esperadas.",
            "Falta una columna indispensable o un tipo es incompatible.",
        )
    if any(unexpected.values()):
        return _result(
            "columns_and_types", "Columnas indispensables y tipos compatibles en las fuentes", ControlStatus.WARNING,
            "La estructura indispensable es válida, pero hay columnas adicionales.", detail,
            "Hay columnas adicionales no esperadas.",
            "Falta una columna indispensable o un tipo es incompatible.",
        )
    return _result(
        "columns_and_types", "Columnas indispensables y tipos compatibles en las fuentes", ControlStatus.PASSED,
        "Todas las columnas indispensables y sus tipos son válidos.", detail,
        "Hay columnas adicionales no esperadas.",
        "Falta una columna indispensable o un tipo es incompatible.",
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
            "dates_and_coverage", "Fechas válidas y cobertura necesaria para el ajuste y la estimación", ControlStatus.FAILED,
            "Hay fechas inválidas o faltan meses necesarios para el ajuste o la estimación.", detail,
            "Los meses sin cobertura de movilidad configurados están ausentes y se dejan sin dato.",
            "Una fecha es inválida o falta un mes necesario para el ajuste o la estimación.",
        )
    if expected_gaps:
        return _result(
            "dates_and_coverage", "Fechas válidas y cobertura necesaria para el ajuste y la estimación", ControlStatus.WARNING,
            "Hay meses sin cobertura de movilidad esperados y no se rellenaron con cero.", detail,
            "Los meses sin cobertura de movilidad configurados están ausentes y se dejan sin dato.",
            "Una fecha es inválida o falta un mes necesario para el ajuste o la estimación.",
        )
    return _result(
        "dates_and_coverage", "Fechas válidas y cobertura necesaria para el ajuste y la estimación", ControlStatus.PASSED,
        "Las fechas y la cobertura necesaria son válidas.", detail,
        "Los meses sin cobertura de movilidad configurados están ausentes y se dejan sin dato.",
        "Una fecha es inválida o falta un mes necesario para el ajuste o la estimación.",
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
            "uniqueness", "Filas únicas según la granularidad declarada de cada fuente", ControlStatus.FAILED,
            "Hay filas duplicadas o la clave de unicidad está incompleta.", detail,
            "Los duplicados solo ocurren antes del primer año de migración que se usa.",
            "Hay duplicados en la movilidad o en los años de migración que usa el pipeline.",
        )
    if ignored_duplicates:
        return _result(
            "uniqueness", "Filas únicas según la granularidad declarada de cada fuente", ControlStatus.WARNING,
            "Los duplicados están solo fuera de los años de migración que se usan.", detail,
            "Los duplicados solo ocurren antes del primer año de migración que se usa.",
            "Hay duplicados en la movilidad o en los años de migración que usa el pipeline.",
        )
    return _result(
        "uniqueness", "Filas únicas según la granularidad declarada de cada fuente", ControlStatus.PASSED,
        "No se encontraron filas duplicadas.", detail,
        "Los duplicados solo ocurren antes del primer año de migración que se usa.",
        "Hay duplicados en la movilidad o en los años de migración que usa el pipeline.",
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
    optional_cells = 0
    for source, frame, columns in (
        ("mobility", mobility, quality.optional_mobility_columns),
        ("migration", migration, quality.optional_migration_columns),
    ):
        for column in columns:
            if column in frame:
                optional_cells += len(frame)
                count = int(frame[column].isna().sum())
                if count:
                    optional_missing[f"{source}.{column}"] = count
    optional_fraction = sum(optional_missing.values()) / optional_cells if optional_cells else 0.0
    detail = {
        "required_missing": required_missing,
        "optional_missing": optional_missing,
        "optional_missing_fraction": optional_fraction,
        "max_optional_missing_fraction": quality.max_optional_missing_fraction,
    }
    if required_missing or optional_fraction > quality.max_optional_missing_fraction:
        return _result(
            "missing_values", "Valores faltantes según si impiden estimar o solo son descriptivos", ControlStatus.FAILED,
            "Faltan valores indispensables para estimar o los faltantes opcionales superan el umbral.", detail,
            "Faltan valores descriptivos opcionales, dentro del umbral configurado.",
            "Falta un valor indispensable para estimar o los faltantes opcionales superan el umbral.",
        )
    if optional_missing:
        return _result(
            "missing_values", "Valores faltantes según si impiden estimar o solo son descriptivos", ControlStatus.WARNING,
            "Solo faltan valores descriptivos opcionales.", detail,
            "Faltan valores descriptivos opcionales, dentro del umbral configurado.",
            "Falta un valor indispensable para estimar o los faltantes opcionales superan el umbral.",
        )
    return _result(
        "missing_values", "Valores faltantes según si impiden estimar o solo son descriptivos", ControlStatus.PASSED,
        "Ningún valor faltante afecta al pipeline.", detail,
        "Faltan valores descriptivos opcionales, dentro del umbral configurado.",
        "Falta un valor indispensable para estimar o los faltantes opcionales superan el umbral.",
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
            "values_and_denominators", "Conteos finitos y no negativos y denominadores nacionales positivos", ControlStatus.FAILED,
            "Hay conteos negativos, valores no finitos o denominadores inválidos.", detail,
            "Hay conteos en cero, pero ningún denominador de ajuste es cero.",
            "Un conteo es negativo o no finito, o un denominador nacional de ajuste no es positivo.",
        )
    row_count = max(len(mobility) + len(migration), 1)
    zero_fraction = sum(zero_counts.values()) / row_count
    if zero_fraction > config.quality.zero_count_warning_fraction:
        return _result(
            "values_and_denominators", "Conteos finitos y no negativos y denominadores nacionales positivos", ControlStatus.WARNING,
            "Hay conteos en cero que no invalidan ningún denominador de ajuste.", detail,
            "Hay conteos en cero, pero ningún denominador de ajuste es cero.",
            "Un conteo es negativo o no finito, o un denominador nacional de ajuste no es positivo.",
        )
    return _result(
        "values_and_denominators", "Conteos finitos y no negativos y denominadores nacionales positivos", ControlStatus.PASSED,
        "Los conteos y los denominadores de ajuste son válidos.", detail,
        "Hay conteos en cero, pero ningún denominador de ajuste es cero.",
        "Un conteo es negativo o no finito, o un denominador nacional de ajuste no es positivo.",
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
        violations.append("la movilidad no viene de la base mensual")
    if context.aggregates_subdestinations:
        violations.append("se suman subdestinos")
    if "destino" in mobility and mobility["destino"].astype(str).str.fullmatch(
        r"\s*total\s*", case=False, na=False
    ).any():
        violations.append("hay filas de total")
    dates = (
        pd.to_datetime(mobility["fecha"], errors="coerce", format="mixed")
        if "fecha" in mobility
        else pd.Series(pd.NaT, index=mobility.index, dtype="datetime64[ns]")
    )
    uncovered = dates.dt.to_period("M").dt.to_timestamp().isin(config.periods.estimate)
    if uncovered.any():
        values = pd.to_numeric(mobility.loc[uncovered, "visitantes"], errors="coerce") if "visitantes" in mobility else pd.Series(dtype=float)
        if values.empty or (values.fillna(0) == 0).any():
            violations.append("meses sin cobertura rellenados con cero")
        else:
            violations.append("hay datos observados en meses configurados sin cobertura")
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
            "methodology", "Regla metodológica: fuente mensual, nivel de subdestino y sin rellenar con cero", ControlStatus.FAILED,
            "Se incumplió una o más reglas metodológicas.", detail,
            "La movilidad tiene meses fuera de la cobertura configurada.",
            "Se usa la base diaria, se suman subdestinos, se arman totales o se rellenan con cero los meses sin cobertura.",
        )
    if unexpected:
        return _result(
            "methodology", "Regla metodológica: fuente mensual, nivel de subdestino y sin rellenar con cero", ControlStatus.WARNING,
            "La metodología es válida, pero la movilidad tiene meses inesperados.", detail,
            "La movilidad tiene meses fuera de la cobertura configurada.",
            "Se usa la base diaria, se suman subdestinos, se arman totales o se rellenan con cero los meses sin cobertura.",
        )
    return _result(
        "methodology", "Regla metodológica: fuente mensual, nivel de subdestino y sin rellenar con cero", ControlStatus.PASSED,
        "Se cumplen las reglas metodológicas automáticas.", detail,
        "La movilidad tiene meses fuera de la cobertura configurada.",
        "Se usa la base diaria, se suman subdestinos, se arman totales o se rellenan con cero los meses sin cobertura.",
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
