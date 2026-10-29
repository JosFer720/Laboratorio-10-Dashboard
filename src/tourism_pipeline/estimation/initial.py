from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.preparation import PreparedData, reparto_factors


RESULT_COLUMNS = (
    "destination",
    "destination_group",
    "period",
    "value",
    "unit",
    "kind",
    "run_id",
    "generated_at",
    "procedure_version",
)
NATIONAL_SERIES_COLUMNS = ("period", "entries", "use")
ESTIMATE_KIND = "estimate"


@dataclass(frozen=True)
class EstimationOutputs:
    results: pd.DataFrame
    factors: pd.DataFrame
    national_series: pd.DataFrame
    coverage: pd.DataFrame


def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{now:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


def estimate_uncovered_months(
    prepared: PreparedData,
    config: PipelineConfig,
    run_id: str,
    generated_at: datetime,
) -> EstimationOutputs:
    """Estima cada mes sin cobertura como factor de reparto por entradas nacionales.

    Un mes a estimar sin entradas nacionales queda fuera del resultado, sin
    convertirse en cero.
    """
    entries = prepared.entries.set_index("period")["entries"]
    estimates, factors = [], []
    for target in config.periods.estimate:
        if target not in entries.index:
            continue
        month_factors = reparto_factors(
            prepared.visitors, prepared.entries, config.periods.fit, target
        )
        factors.append(month_factors)
        estimates.append(
            month_factors.assign(
                period=target, value=month_factors["factor"] * entries[target]
            )
        )

    results = pd.concat(estimates, ignore_index=True) if estimates else pd.DataFrame(
        columns=["destination", "destination_group", "period", "value"]
    )
    results = results.assign(
        unit=config.parameters.unit,
        kind=ESTIMATE_KIND,
        run_id=run_id,
        generated_at=generated_at.isoformat(timespec="seconds"),
        procedure_version=config.parameters.procedure_version,
    )
    factor_table = pd.concat(factors, ignore_index=True) if factors else pd.DataFrame()
    return EstimationOutputs(
        results=results.loc[:, RESULT_COLUMNS].reset_index(drop=True),
        factors=factor_table,
        national_series=_national_series_used(prepared.entries, config),
        coverage=prepared.coverage,
    )


def _national_series_used(entries: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    uses = {month: "ajuste" for month in config.periods.fit}
    uses.update({month: "estimación" for month in config.periods.estimate})
    used = entries.loc[entries["period"].isin(uses)].copy()
    used["use"] = used["period"].map(uses)
    return used.loc[:, NATIONAL_SERIES_COLUMNS].reset_index(drop=True)


def write_outputs(
    outputs: EstimationOutputs, directory: str | Path, config: PipelineConfig
) -> dict[str, Path]:
    """Escribe las estimaciones y los archivos que permiten reproducirlas."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "results": (outputs.results, config.paths.results_file),
        "factors": (outputs.factors, config.paths.factors_file),
        "national_series": (outputs.national_series, config.paths.national_series_file),
        "coverage": (outputs.coverage, config.paths.coverage_file),
    }
    written = {}
    for name, (table, file_name) in files.items():
        path = directory / file_name
        table.to_csv(path, index=False, date_format="%Y-%m-%d")
        written[name] = path
    return written
