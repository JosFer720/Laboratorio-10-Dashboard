from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.estimation import ESTIMATE_KIND, RESULT_COLUMNS, EvaluationResult
from tourism_pipeline.validation import QualityReport


APPROVED = "aprobada"
REJECTED = "rechazada"


@dataclass(frozen=True)
class RuleCheck:
    name: str
    passed: bool
    message: str


@dataclass(frozen=True)
class AcceptanceDecision:
    approved: bool
    checks: tuple[RuleCheck, ...]
    thresholds: dict[str, float]

    @property
    def verdict(self) -> str:
        return APPROVED if self.approved else REJECTED

    @property
    def reasons(self) -> tuple[str, ...]:
        """Razones del rechazo; vacío cuando la versión se aprueba."""
        return tuple(check.message for check in self.checks if not check.passed)

    def as_record(self) -> dict:
        return {
            "verdict": self.verdict,
            "approved": self.approved,
            "reasons": list(self.reasons),
            "checks": [asdict(check) for check in self.checks],
            "thresholds": dict(self.thresholds),
        }


def decide_acceptance(
    quality: QualityReport,
    results: pd.DataFrame,
    evaluation: EvaluationResult,
    expected_destinations: Iterable[str],
    config: PipelineConfig,
) -> AcceptanceDecision:
    """Aplica la regla de aceptación fijada en la configuración.

    Combina los controles de calidad, la integridad de las salidas y el
    desempeño en la evaluación temporal. Superar a las referencias sencillas no
    forma parte de la regla.
    """
    rule = config.acceptance
    destinations = set(expected_destinations)
    checks = (
        _check_quality(quality),
        _check_integrity(results, destinations, config),
        _check_evaluation_coverage(evaluation, destinations, rule.min_evaluated_months),
        _check_performance(evaluation, rule.max_mape),
    )
    return AcceptanceDecision(
        approved=all(check.passed for check in checks),
        checks=checks,
        thresholds={
            "max_mape": rule.max_mape,
            "min_evaluated_months": float(rule.min_evaluated_months),
        },
    )


def _check_quality(quality: QualityReport) -> RuleCheck:
    failed = [result.name for result in quality.results if result.stops_pipeline]
    if failed:
        return RuleCheck("quality", False, "Fallaron controles críticos: " + ", ".join(failed) + ".")
    return RuleCheck("quality", True, "Ningún control de calidad crítico falló.")


def _check_integrity(
    results: pd.DataFrame, destinations: set[str], config: PipelineConfig
) -> RuleCheck:
    problems = []
    if tuple(results.columns) != RESULT_COLUMNS:
        problems.append("las columnas no coinciden con las del archivo de resultados")
    else:
        if results.isna().any().any():
            problems.append("hay celdas vacías")
        values = pd.to_numeric(results["value"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(values).all():
            problems.append("hay valores no finitos")
        elif (values <= 0).any():
            problems.append("hay estimaciones negativas o en cero")
        if not results["kind"].eq(ESTIMATE_KIND).all():
            problems.append("hay filas no rotuladas como estimación")
        if not results["unit"].eq(config.parameters.unit).all():
            problems.append("la unidad no coincide con la configurada")
        if results.duplicated(["destination", "period"]).any():
            problems.append("hay subdestinos repetidos en un mismo mes")
        found = set(zip(results["destination"], pd.to_datetime(results["period"])))
        missing = [
            f"{destination} {month:%Y-%m}"
            for month in config.periods.estimate
            for destination in sorted(destinations)
            if (destination, month) not in found
        ]
        if missing:
            problems.append(f"faltan {len(missing)} estimaciones, por ejemplo {missing[0]}")
    if problems:
        return RuleCheck("integrity", False, "Salidas incompletas: " + "; ".join(problems) + ".")
    return RuleCheck(
        "integrity", True, "Las estimaciones están completas, son positivas y finitas."
    )


def _check_evaluation_coverage(
    evaluation: EvaluationResult, destinations: set[str], minimum: int
) -> RuleCheck:
    months = len(evaluation.evaluated_months)
    if months < minimum:
        return RuleCheck(
            "evaluation_coverage",
            False,
            f"Solo se pudieron evaluar {months} meses y la regla pide al menos {minimum}.",
        )
    per_month = evaluation.predictions.groupby("period")["destination"].nunique()
    incomplete = per_month.loc[per_month < len(destinations)]
    if not incomplete.empty:
        return RuleCheck(
            "evaluation_coverage",
            False,
            f"En {incomplete.index[0]:%Y-%m} no se evaluaron todos los subdestinos.",
        )
    return RuleCheck(
        "evaluation_coverage",
        True,
        f"Se evaluaron {months} meses con todos los subdestinos.",
    )


def _check_performance(evaluation: EvaluationResult, max_mape: float) -> RuleCheck:
    mape = evaluation.metrics["candidate"]["mape"]
    if not np.isfinite(mape):
        return RuleCheck("performance", False, "No hay error de evaluación para comparar con el umbral.")
    if mape > max_mape:
        return RuleCheck(
            "performance",
            False,
            f"El MAPE de la evaluación es {mape:.1f} %, mayor que el máximo de {max_mape:.1f} %.",
        )
    return RuleCheck(
        "performance",
        True,
        f"El MAPE de la evaluación es {mape:.1f} %, dentro del máximo de {max_mape:.1f} %.",
    )
