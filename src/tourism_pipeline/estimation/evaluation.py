from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.preparation import PreparedData, reparto_factors


DESTINATION_COLUMNS = ["sheet", "destination_group", "destination"]
METHODS = {
    "candidate": "Factor de reparto",
    "last_observed": "Último valor observado",
    "historical_mean": "Promedio de los meses anteriores",
}
PREDICTION_COLUMNS = (
    *DESTINATION_COLUMNS,
    "period",
    "observed",
    *METHODS,
)
SUMMARY_COLUMNS = (*DESTINATION_COLUMNS, "method", "months", "mae", "rmse", "mape")


@dataclass(frozen=True)
class EvaluationResult:
    predictions: pd.DataFrame
    by_destination: pd.DataFrame
    metrics: dict[str, dict[str, float]]
    evaluated_months: tuple[pd.Timestamp, ...]
    skipped_months: tuple[pd.Timestamp, ...]

    def flat_metrics(self) -> dict[str, float]:
        """Métricas listas para registrarse, por ejemplo `candidate.mape`."""
        flat = {
            f"{method}.{name}": value
            for method, values in self.metrics.items()
            for name, value in values.items()
        }
        flat["evaluated_months"] = float(len(self.evaluated_months))
        return flat


def error_metrics(observed: pd.Series, predicted: pd.Series) -> dict[str, float]:
    """MAE, RMSE y MAPE. El MAPE excluye los observados en cero y los cuenta aparte."""
    error = predicted.to_numpy(dtype=float) - observed.to_numpy(dtype=float)
    observed_values = observed.to_numpy(dtype=float)
    nonzero = observed_values != 0
    return {
        "mae": float(np.mean(np.abs(error))) if error.size else float("nan"),
        "rmse": float(np.sqrt(np.mean(error**2))) if error.size else float("nan"),
        "mape": (
            float(np.mean(np.abs(error[nonzero]) / observed_values[nonzero]) * 100)
            if nonzero.any()
            else float("nan")
        ),
        "n": float(error.size),
        "zero_observed_excluded": float((~nonzero).sum()),
    }


def evaluate_procedure(prepared: PreparedData, config: PipelineConfig) -> EvaluationResult:
    """Oculta cada mes de evaluación, en orden, y lo estima solo con meses anteriores.

    El factor de reparto y las dos referencias sencillas usan únicamente la
    movilidad observada antes del mes evaluado. Del mes evaluado solo se usan sus
    entradas nacionales, igual que al estimar un mes sin cobertura.
    """
    entries = prepared.entries.set_index("period")["entries"]
    frames, evaluated, skipped = [], [], []
    for month in config.periods.evaluation:
        observed = prepared.visitors.loc[prepared.visitors["period"] == month]
        if observed.empty or month not in entries.index:
            skipped.append(month)
            continue
        history = prepared.visitors.loc[prepared.visitors["period"] < month]
        factors = reparto_factors(history, prepared.entries, config.periods.fit, month)
        ordered = history.sort_values("period", kind="stable")
        references = ordered.groupby(DESTINATION_COLUMNS, sort=True).agg(
            last_observed=("visitors", "last"),
            historical_mean=("visitors", "mean"),
        )
        rows = (
            observed.rename(columns={"visitors": "observed"})
            .merge(factors.loc[:, [*DESTINATION_COLUMNS, "factor"]], on=DESTINATION_COLUMNS)
            .merge(references.reset_index(), on=DESTINATION_COLUMNS)
        )
        rows["candidate"] = rows["factor"] * entries[month]
        frames.append(rows.loc[:, PREDICTION_COLUMNS])
        evaluated.append(month)

    predictions = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=PREDICTION_COLUMNS)
    )
    metrics = {
        method: error_metrics(predictions["observed"], predictions[method])
        for method in METHODS
    }
    return EvaluationResult(
        predictions=predictions,
        by_destination=_by_destination(predictions),
        metrics=metrics,
        evaluated_months=tuple(evaluated),
        skipped_months=tuple(skipped),
    )


def _by_destination(predictions: pd.DataFrame) -> pd.DataFrame:
    records = []
    for keys, rows in predictions.groupby(DESTINATION_COLUMNS, sort=True):
        for method in METHODS:
            values = error_metrics(rows["observed"], rows[method])
            records.append(
                {
                    **dict(zip(DESTINATION_COLUMNS, keys)),
                    "method": method,
                    "months": int(values["n"]),
                    "mae": values["mae"],
                    "rmse": values["rmse"],
                    "mape": values["mape"],
                }
            )
    return pd.DataFrame(records, columns=SUMMARY_COLUMNS)


def write_evaluation(
    evaluation: EvaluationResult, directory: str | Path, config: PipelineConfig
) -> dict[str, Path]:
    directory = Path(directory)
    files = {
        "evaluation": (evaluation.predictions, config.paths.evaluation_file),
        "evaluation_summary": (evaluation.by_destination, config.paths.evaluation_summary_file),
    }
    written = {}
    for name, (table, file_name) in files.items():
        path = directory / file_name
        table.to_csv(path, index=False, date_format="%Y-%m-%d")
        written[name] = path
    return written
