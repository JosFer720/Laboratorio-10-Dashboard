from __future__ import annotations

import os
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "pipeline.yaml"


class ConfigError(ValueError):
    """La configuración del pipeline es incompleta o inconsistente."""


@dataclass(frozen=True)
class PathsConfig:
    data_dir: Path
    mobility_file: str
    mobility_sheets: tuple[str, ...]
    migration_file: str
    migration_sheet: str
    output_dir: Path
    reports_dir: str
    results_file: str
    factors_file: str
    national_series_file: str
    coverage_file: str
    evaluation_file: str
    evaluation_summary_file: str

    @property
    def reports_path(self) -> Path:
        return self.output_dir / self.reports_dir

    @property
    def mobility_path(self) -> Path:
        return self.data_dir / self.mobility_file

    @property
    def migration_path(self) -> Path:
        return self.data_dir / self.migration_file


@dataclass(frozen=True)
class PeriodsConfig:
    mobility_coverage: tuple[pd.Timestamp, ...]
    migration_coverage: tuple[pd.Timestamp, ...]
    fit: tuple[pd.Timestamp, ...]
    evaluation: tuple[pd.Timestamp, ...]
    estimate: tuple[pd.Timestamp, ...]


@dataclass(frozen=True)
class MigrationConfig:
    traveler_types: tuple[str, ...]
    first_year: int


@dataclass(frozen=True)
class ParametersConfig:
    procedure_version: str
    unit: str
    seed: int
    reparto_factor: str
    migration: MigrationConfig


@dataclass(frozen=True)
class QualityConfig:
    mobility_columns: tuple[str, ...]
    mobility_key: tuple[str, ...]
    migration_key: tuple[str, ...]
    mobility_segments: tuple[str, ...]
    migration_columns: tuple[str, ...]
    mobility_numeric_columns: tuple[str, ...]
    migration_numeric_columns: tuple[str, ...]
    required_non_null_mobility: tuple[str, ...]
    required_non_null_migration: tuple[str, ...]
    optional_mobility_columns: tuple[str, ...]
    optional_migration_columns: tuple[str, ...]
    max_optional_missing_fraction: float
    zero_count_warning_fraction: float


@dataclass(frozen=True)
class AcceptanceConfig:
    max_mape: float
    min_evaluated_months: int


@dataclass(frozen=True)
class PublicationConfig:
    versions_dir: Path


@dataclass(frozen=True)
class TrackingConfig:
    uri: str
    experiment_name: str
    reproducibility_tolerance: float


@dataclass(frozen=True)
class MonitoringConfig:
    max_estimate_change_fraction: float = 0.5
    max_missing_fraction_change: float = 0.01


@dataclass(frozen=True)
class PipelineConfig:
    paths: PathsConfig
    periods: PeriodsConfig
    parameters: ParametersConfig
    quality: QualityConfig
    tracking: TrackingConfig
    acceptance: AcceptanceConfig
    publication: PublicationConfig
    monitoring: MonitoringConfig = MonitoringConfig()


def expand_months(ranges: list[Mapping[str, str]] | None, name: str) -> tuple[pd.Timestamp, ...]:
    """Convierte rangos inclusivos de meses (AAAA-MM) en una lista ordenada de meses."""
    if not ranges:
        raise ConfigError(f"El período {name} debe tener al menos un rango.")
    months: set[pd.Timestamp] = set()
    for item in ranges:
        try:
            start = pd.Period(str(item["start"]), freq="M")
            end = pd.Period(str(item["end"]), freq="M")
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigError(
                f"El período {name} necesita start y end con formato AAAA-MM."
            ) from exc
        if end < start:
            raise ConfigError(f"El período {name} termina antes de empezar.")
        months.update(period.to_timestamp() for period in pd.period_range(start, end, freq="M"))
    return tuple(sorted(months))


def load_config(
    path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> PipelineConfig:
    values = os.environ if env is None else env
    config_path = Path(path or values.get("PIPELINE_CONFIG") or DEFAULT_CONFIG_PATH)
    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"No se pudo leer el archivo de configuración {config_path}.") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"El archivo de configuración {config_path} no es YAML válido.") from exc
    if not isinstance(raw, dict):
        raise ConfigError("El archivo de configuración debe ser un mapa YAML.")

    try:
        paths = _build_paths(raw["paths"], values)
        config = PipelineConfig(
            paths=paths,
            periods=_build_periods(raw["periods"]),
            parameters=_build_parameters(raw["parameters"]),
            quality=_build_quality(raw["quality"]),
            tracking=_build_tracking(raw["tracking"], values, paths),
            acceptance=_build_acceptance(raw["acceptance"]),
            publication=_build_publication(raw["publication"], values, paths),
            monitoring=MonitoringConfig(**raw.get("monitoring", {})),
        )
    except KeyError as exc:
        raise ConfigError(f"Falta la clave {exc} en la configuración.") from exc
    _check_periods(config.periods)
    _check_quality(config.quality)
    if config.tracking.reproducibility_tolerance < 0:
        raise ConfigError("La tolerancia de reproducibilidad no puede ser negativa.")
    _check_acceptance(config.acceptance, config.periods)
    if any(not math.isfinite(value) or value < 0 for value in (
        config.monitoring.max_estimate_change_fraction,
        config.monitoring.max_missing_fraction_change,
    )):
        raise ConfigError("Los umbrales de monitoreo deben ser finitos y no negativos.")
    return config


def _build_paths(raw: Mapping[str, Any], env: Mapping[str, str]) -> PathsConfig:
    data_dir = env.get("INGUAT_DATA_DIR") or raw.get("data_dir")
    if not data_dir:
        raise ConfigError(
            "Falta la carpeta de datos: define la variable de entorno INGUAT_DATA_DIR."
        )
    return PathsConfig(
        data_dir=Path(data_dir),
        mobility_file=str(raw["mobility_file"]),
        mobility_sheets=tuple(raw["mobility_sheets"]),
        migration_file=str(raw["migration_file"]),
        migration_sheet=str(raw["migration_sheet"]),
        output_dir=Path(env.get("PIPELINE_OUTPUT_DIR") or raw["output_dir"]),
        reports_dir=str(raw["reports_dir"]),
        results_file=str(raw["results_file"]),
        factors_file=str(raw["factors_file"]),
        national_series_file=str(raw["national_series_file"]),
        coverage_file=str(raw["coverage_file"]),
        evaluation_file=str(raw["evaluation_file"]),
        evaluation_summary_file=str(raw["evaluation_summary_file"]),
    )


def _build_periods(raw: Mapping[str, Any]) -> PeriodsConfig:
    return PeriodsConfig(
        mobility_coverage=expand_months(raw["mobility_coverage"], "mobility_coverage"),
        migration_coverage=expand_months(raw["migration_coverage"], "migration_coverage"),
        fit=expand_months(raw["fit"], "fit"),
        evaluation=expand_months(raw["evaluation"], "evaluation"),
        estimate=expand_months(raw["estimate"], "estimate"),
    )


def _build_parameters(raw: Mapping[str, Any]) -> ParametersConfig:
    migration = raw["migration"]
    return ParametersConfig(
        procedure_version=str(raw["procedure_version"]),
        unit=str(raw["unit"]),
        seed=int(raw["seed"]),
        reparto_factor=str(raw["reparto_factor"]),
        migration=MigrationConfig(
            traveler_types=tuple(migration["traveler_types"]),
            first_year=int(migration["first_year"]),
        ),
    )


def _build_quality(raw: Mapping[str, Any]) -> QualityConfig:
    thresholds = raw["thresholds"]
    return QualityConfig(
        mobility_columns=tuple(raw["mobility_columns"]),
        mobility_key=tuple(raw["mobility_key"]),
        migration_key=tuple(raw["migration_key"]),
        mobility_segments=tuple(raw["mobility_segments"]),
        migration_columns=tuple(raw["migration_columns"]),
        mobility_numeric_columns=tuple(raw["mobility_numeric_columns"]),
        migration_numeric_columns=tuple(raw["migration_numeric_columns"]),
        required_non_null_mobility=tuple(raw["required_non_null_mobility"]),
        required_non_null_migration=tuple(raw["required_non_null_migration"]),
        optional_mobility_columns=tuple(raw["optional_mobility_columns"]),
        optional_migration_columns=tuple(raw["optional_migration_columns"]),
        max_optional_missing_fraction=float(thresholds["max_optional_missing_fraction"]),
        zero_count_warning_fraction=float(thresholds["zero_count_warning_fraction"]),
    )


def _build_tracking(
    raw: Mapping[str, Any], values: Mapping[str, str], paths: PathsConfig
) -> TrackingConfig:
    uri = values.get("MLFLOW_TRACKING_URI") or str(paths.output_dir / str(raw["directory"]))
    tolerance = values.get("PIPELINE_REPRODUCIBILITY_TOLERANCE")
    return TrackingConfig(
        uri=uri,
        experiment_name=values.get("MLFLOW_EXPERIMENT_NAME") or str(raw["experiment_name"]),
        reproducibility_tolerance=float(
            tolerance if tolerance is not None else raw["reproducibility_tolerance"]
        ),
    )


def _build_acceptance(raw: Mapping[str, Any]) -> AcceptanceConfig:
    return AcceptanceConfig(
        max_mape=float(raw["max_mape"]),
        min_evaluated_months=int(raw["min_evaluated_months"]),
    )


def _build_publication(
    raw: Mapping[str, Any], values: Mapping[str, str], paths: PathsConfig
) -> PublicationConfig:
    versions = values.get("PIPELINE_VERSIONS_DIR") or paths.output_dir / str(raw["versions_dir"])
    return PublicationConfig(versions_dir=Path(versions))


def _check_acceptance(acceptance: AcceptanceConfig, periods: PeriodsConfig) -> None:
    if acceptance.max_mape <= 0:
        raise ConfigError("El umbral max_mape de la regla de aceptación debe ser positivo.")
    if not 1 <= acceptance.min_evaluated_months <= len(periods.evaluation):
        raise ConfigError(
            "min_evaluated_months debe estar entre 1 y el número de meses de evaluación."
        )


def _check_periods(periods: PeriodsConfig) -> None:
    mobility = set(periods.mobility_coverage)
    migration = set(periods.migration_coverage)
    fit = set(periods.fit)
    if not fit <= mobility & migration:
        raise ConfigError(
            "Los meses de ajuste deben tener movilidad y entradas nacionales observadas."
        )
    if not set(periods.evaluation) <= fit:
        raise ConfigError("Los meses de evaluación deben estar entre los meses de ajuste.")
    if set(periods.estimate) & mobility:
        raise ConfigError(
            "Los meses a estimar no pueden tener cobertura de movilidad."
        )
    if not set(periods.estimate) <= migration:
        raise ConfigError(
            "Los meses a estimar necesitan entradas nacionales para calcular la estimación."
        )


def _check_quality(quality: QualityConfig) -> None:
    thresholds = (
        quality.max_optional_missing_fraction,
        quality.zero_count_warning_fraction,
    )
    if any(value < 0 or value > 1 for value in thresholds):
        raise ConfigError("Los umbrales de calidad deben ser fracciones entre 0 y 1.")
