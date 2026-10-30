from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.estimation import (
    EstimationOutputs,
    estimate_uncovered_months,
    new_run_id,
    write_outputs,
)
from tourism_pipeline.ingestion import FileFingerprint, read_migration, read_mobility
from tourism_pipeline.preparation import prepare
from tourism_pipeline.tracking import RunTracker
from tourism_pipeline.validation import MethodologyContext, QualityReport, run_quality_controls


logger = logging.getLogger("tourism_pipeline")

STAGING_PREFIX = ".staging-"


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    generated_at: datetime
    quality_report: QualityReport
    sources: dict[str, FileFingerprint]
    files: dict[str, Path]
    tracking_run_id: str


def run_pipeline(config: PipelineConfig, now: datetime | None = None) -> PipelineRun:
    """Ejecuta lectura, validación, preparación, estimación y almacenamiento.

    Los resultados se escriben primero en una carpeta temporal y solo se mueven a
    la carpeta de salida cuando todas las etapas terminaron bien. Si un control
    crítico falla, el reporte de controles queda escrito, la ejecución se detiene
    con `QualityControlError` y los resultados anteriores no se tocan.
    """
    generated_at = now or datetime.now(timezone.utc)
    run_id = new_run_id(generated_at)
    logger.info("Ejecución %s", run_id)
    tracker = RunTracker(config, run_id, generated_at)

    try:
        logger.info("Etapa 1/5: lectura de las fuentes")
        mobility = read_mobility(config)
        migration = read_migration(config)
        sources = {source.name: source.fingerprint for source in (mobility, migration)}
        tracker.log_sources(sources)

        logger.info("Etapa 2/5: controles de calidad")
        report = run_quality_controls(
            mobility.data,
            migration.data,
            config,
            config.paths.reports_path / f"quality_{run_id}.json",
            run_id,
            generated_at,
            methodology=MethodologyContext(
                mobility_source="monthly", aggregates_subdestinations=False
            ),
        )
        tracker.log_quality(report)

        logger.info("Etapa 3/5: preparación de las series y cobertura")
        prepared = prepare(mobility.data, migration.data, config)

        logger.info("Etapa 4/5: factor de reparto y estimación de los meses sin cobertura")
        outputs = estimate_uncovered_months(prepared, config, run_id, generated_at)

        logger.info("Etapa 5/5: almacenamiento de los resultados")
        files = _store(outputs, config)
        tracker.log_outputs(files)
        tracker.finish()
        return PipelineRun(run_id, generated_at, report, sources, files, tracker.run_id)
    except Exception as exc:
        report = getattr(exc, "report", None)
        if report is not None:
            tracker.log_quality(report)
        tracker.fail(str(exc))
        raise


def _store(outputs: EstimationOutputs, config: PipelineConfig) -> dict[str, Path]:
    output_dir = config.paths.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=output_dir))
    try:
        staged = write_outputs(outputs, staging, config)
        files = {}
        for name, path in staged.items():
            target = output_dir / path.name
            os.replace(path, target)
            files[name] = target
        return files
    finally:
        shutil.rmtree(staging, ignore_errors=True)
