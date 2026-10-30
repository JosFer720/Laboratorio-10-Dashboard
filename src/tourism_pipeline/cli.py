from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from tourism_pipeline.config import ConfigError, load_config
from tourism_pipeline.estimation import METHODS
from tourism_pipeline.ingestion import SourceReadError
from tourism_pipeline.pipeline import logger, run_pipeline
from tourism_pipeline.preparation import RepartoError
from tourism_pipeline.validation import ControlStatus, QualityControlError


EXIT_OK = 0
EXIT_CONTROL_FAILED = 2
EXIT_SETUP_ERROR = 3
EXIT_REJECTED = 4

STATUS_LABELS = {
    ControlStatus.PASSED: "correcto",
    ControlStatus.WARNING: "advertencia",
    ControlStatus.FAILED: "falló",
}


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_pipeline",
        description=(
            "Lee las fuentes, valida los datos, estima los meses sin cobertura, "
            "evalúa el procedimiento y publica la versión si se aprueba."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Archivo de configuración (por defecto, PIPELINE_CONFIG o config/pipeline.yaml).",
    )
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    try:
        config = load_config(args.config, env=env)
        run = run_pipeline(config)
    except ConfigError as exc:
        logger.error("Configuración inválida: %s", exc)
        return EXIT_SETUP_ERROR
    except (SourceReadError, RepartoError) as exc:
        logger.error("No se pudo completar el pipeline: %s", exc)
        return EXIT_SETUP_ERROR
    except QualityControlError as exc:
        logger.error("El pipeline se detuvo: %s", exc)
        for result in exc.report.results:
            logger.error("  %s: %s. %s", result.name, STATUS_LABELS[result.status], result.message)
        logger.error("Reporte de controles: %s", exc.report.path)
        logger.error("Los resultados anteriores no se reemplazaron.")
        return EXIT_CONTROL_FAILED

    logger.info("Controles de calidad:")
    for result in run.quality_report.results:
        logger.info("  %s: %s. %s", result.name, STATUS_LABELS[result.status], result.message)
    logger.info("Reporte de controles: %s", run.quality_report.path)
    for name, path in run.files.items():
        logger.info("Resultado %s: %s", name, path)
    _log_evaluation(run)
    logger.info("Regla de aceptación: versión %s.", run.acceptance.verdict)
    for reason in run.acceptance.reasons:
        logger.info("  %s", reason)
    if run.published:
        logger.info("Versión publicada y vigente: %s", run.published.path)
    else:
        logger.info(
            "La versión no se publicó. Versión vigente: %s",
            run.current.version_id if run.current else "ninguna aprobada todavía",
        )
    logger.info("Registro MLflow: %s", run.tracking_run_id)
    logger.info("Ejecución %s terminada.", run.run_id)
    return EXIT_OK if run.acceptance.approved else EXIT_REJECTED


def _log_evaluation(run) -> None:
    months = ", ".join(f"{month:%Y-%m}" for month in run.evaluation.evaluated_months)
    logger.info("Evaluación temporal (%s):", months or "sin meses evaluados")
    for method, label in METHODS.items():
        values = run.evaluation.metrics[method]
        logger.info(
            "  %s: MAE %.0f, RMSE %.0f, MAPE %.1f %%",
            label,
            values["mae"],
            values["rmse"],
            values["mape"],
        )


if __name__ == "__main__":
    raise SystemExit(main())
