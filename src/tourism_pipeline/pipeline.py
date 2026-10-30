from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.monitoring import ExecutionRecord, check_monitoring, source_snapshot
from tourism_pipeline.estimation import (
    EstimationOutputs,
    EvaluationResult,
    estimate_uncovered_months,
    evaluate_procedure,
    new_run_id,
    write_evaluation,
    write_outputs,
)
from tourism_pipeline.ingestion import FileFingerprint, read_migration, read_mobility
from tourism_pipeline.preparation import prepare
from tourism_pipeline.publication import (
    AcceptanceDecision,
    PublishedVersion,
    current_version,
    decide_acceptance,
    publish_version,
)
from tourism_pipeline.tracking import (
    RunTracker,
    effective_config,
    git_commit,
    record_evaluation_metrics,
)
from tourism_pipeline.validation import MethodologyContext, QualityReport, run_quality_controls


logger = logging.getLogger("tourism_pipeline")

STAGING_PREFIX = ".staging-"
CONFIG_DOCUMENT = "effective_config.json"


@dataclass(frozen=True)
class PipelineRun:
    run_id: str
    generated_at: datetime
    quality_report: QualityReport
    sources: dict[str, FileFingerprint]
    files: dict[str, Path]
    tracking_run_id: str
    evaluation: EvaluationResult
    acceptance: AcceptanceDecision
    published: PublishedVersion | None
    current: PublishedVersion | None


def run_pipeline(
    config: PipelineConfig, now: datetime | None = None, publish: bool = True
) -> PipelineRun:
    """Ejecuta lectura, validación, preparación, estimación, evaluación y publicación.

    Los resultados se escriben primero en una carpeta temporal y solo se mueven a
    la carpeta de salida cuando todas las etapas terminaron bien. Si un control
    crítico falla, el reporte de controles queda escrito, la ejecución se detiene
    con `QualityControlError` y los resultados anteriores no se tocan. Solo una
    candidata aprobada por la regla de aceptación pasa a ser la versión vigente;
    si se rechaza, la vigente no cambia.
    """
    generated_at = now or datetime.now(timezone.utc)
    run_id = new_run_id(generated_at)
    logger.info("Ejecución %s", run_id)
    execution = ExecutionRecord(config, run_id, generated_at)
    tracker = None
    outputs = None
    snapshot = None

    try:
        tracker = RunTracker(config, run_id, generated_at)
        execution.data["tracking_run_id"] = tracker.run_id
        logger.info("Etapa 1/7: lectura de las fuentes")
        mobility = read_mobility(config)
        migration = read_migration(config)
        sources = {source.name: source.fingerprint for source in (mobility, migration)}
        tracker.log_sources(sources)
        execution.completed("reading")
        snapshot = source_snapshot(mobility.data, migration.data, config)
        execution.data["source_snapshot"] = snapshot

        logger.info("Etapa 2/7: controles de calidad")
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
        execution.completed("quality")
        execution.data["warnings"].extend(result.message for result in report.results if result.status.value == "warning")

        logger.info("Etapa 3/7: preparación de las series y cobertura")
        prepared = prepare(mobility.data, migration.data, config)
        execution.completed("preparation")

        logger.info("Etapa 4/7: factor de reparto y estimación de los meses sin cobertura")
        outputs = estimate_uncovered_months(prepared, config, run_id, generated_at)
        execution.completed("estimation")
        previous = current_version(config.publication.versions_dir)
        previous_results = None
        if previous:
            previous_config = json.loads(previous.file(CONFIG_DOCUMENT).read_text(encoding="utf-8"))
            previous_results = pd.read_csv(previous.file(previous_config["paths"]["results_file"]))
        execution.data["monitoring"] = check_monitoring(
            snapshot, outputs.results, config, execution.previous, previous_results
        )
        execution.data["warnings"].extend(
            alert for check in execution.data["monitoring"].values() for alert in check["alerts"]
        )
        execution.completed("monitoring")

        logger.info("Etapa 5/7: evaluación temporal con meses ocultos")
        evaluation = evaluate_procedure(prepared, config)
        execution.completed("evaluation")

        logger.info("Etapa 6/7: regla de aceptación")
        decision = decide_acceptance(
            report,
            outputs.results,
            evaluation,
            prepared.visitors["destination"].unique(),
            config,
        )
        _write_acceptance_report(decision, evaluation, config, run_id)
        execution.completed("acceptance")

        logger.info("Etapa 7/7: almacenamiento y publicación")
        files = _store(outputs, evaluation, config)
        tracker.log_outputs(files)
        record_evaluation_metrics(config, tracker.run_id, _finite(evaluation.flat_metrics()))
        tracker.log_acceptance(
            decision.as_record(),
            ",".join(f"{month:%Y-%m}" for month in evaluation.evaluated_months),
        )
        published = None
        if publish and decision.approved:
            observed_path = config.paths.output_dir / "observed.csv"
            prepared.visitors.to_csv(observed_path, index=False, date_format="%Y-%m-%d")
            tracker.log_outputs({"observed": observed_path})
            published = publish_version(
                config.publication.versions_dir,
                run_id,
                {**files, "observed": observed_path},
                _version_metadata(run_id, generated_at, tracker.run_id, sources, evaluation, decision, config),
                documents={CONFIG_DOCUMENT: effective_config(config)},
            )
        current = current_version(config.publication.versions_dir)
        tracker.log_publication(
            published.version_id if published else None,
            current.version_id if current else None,
        )
        execution.data["publication"] = "published" if published else ("rejected" if not decision.approved else "disabled")
        execution.data["current_version"] = current.version_id if current else None
        execution.completed("publication")
        tracker.client.log_artifact(tracker.run_id, str(execution.write()), artifact_path="monitoring")
        tracker.finish()
        return PipelineRun(
            run_id,
            generated_at,
            report,
            sources,
            files,
            tracker.run_id,
            evaluation,
            decision,
            published,
            current,
        )
    except Exception as exc:
        report = getattr(exc, "report", None)
        execution.data["errors"].append(str(exc))
        if snapshot is not None and "monitoring" not in execution.data:
            execution.data["monitoring"] = check_monitoring(snapshot, None, config, execution.previous)
            execution.data["warnings"].extend(alert for check in execution.data["monitoring"].values() for alert in check["alerts"])
        execution.write()
        if tracker is not None:
            if report is not None:
                tracker.log_quality(report)
            tracker.client.log_artifact(tracker.run_id, str(execution.path), artifact_path="monitoring")
            tracker.fail(str(exc))
        raise


def _finite(metrics: dict[str, float]) -> dict[str, float]:
    # Una métrica sin valor (por ejemplo, el MAPE sin observados distintos de
    # cero) no se registra: no se inventan valores.
    return {
        f"evaluation.{name}": value
        for name, value in metrics.items()
        if value == value and value not in (float("inf"), float("-inf"))
    }


def _version_metadata(
    run_id: str,
    generated_at: datetime,
    tracking_run_id: str,
    sources: dict[str, FileFingerprint],
    evaluation: EvaluationResult,
    decision: AcceptanceDecision,
    config: PipelineConfig,
) -> dict:
    candidate = evaluation.metrics["candidate"]
    return {
        "run_id": run_id,
        "tracking_run_id": tracking_run_id,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "git_commit": git_commit(),
        "procedure_version": config.parameters.procedure_version,
        "unit": config.parameters.unit,
        "estimated_periods": [f"{month:%Y-%m}" for month in config.periods.estimate],
        "validation": {
            "metric": "MAPE",
            "mape": candidate["mape"],
            "mae": candidate["mae"],
            "rmse": candidate["rmse"],
            "evaluated_periods": [f"{month:%Y-%m}" for month in evaluation.evaluated_months],
            "references": {
                method: values["mape"]
                for method, values in evaluation.metrics.items()
                if method != "candidate"
            },
        },
        "acceptance": decision.as_record(),
        "sources": {name: asdict(fingerprint) for name, fingerprint in sources.items()},
    }


def _write_acceptance_report(
    decision: AcceptanceDecision,
    evaluation: EvaluationResult,
    config: PipelineConfig,
    run_id: str,
) -> Path:
    reports = config.paths.reports_path
    reports.mkdir(parents=True, exist_ok=True)
    path = reports / f"acceptance_{run_id}.json"
    content = {
        "run_id": run_id,
        **decision.as_record(),
        "evaluation": {
            "evaluated_periods": [f"{month:%Y-%m}" for month in evaluation.evaluated_months],
            "skipped_periods": [f"{month:%Y-%m}" for month in evaluation.skipped_months],
            "metrics": evaluation.metrics,
        },
    }
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _store(
    outputs: EstimationOutputs, evaluation: EvaluationResult, config: PipelineConfig
) -> dict[str, Path]:
    output_dir = config.paths.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=STAGING_PREFIX, dir=output_dir))
    try:
        staged = write_outputs(outputs, staging, config)
        staged.update(write_evaluation(evaluation, staging, config))
        files = {}
        for name, path in staged.items():
            target = output_dir / path.name
            os.replace(path, target)
            files[name] = target
        return files
    finally:
        shutil.rmtree(staging, ignore_errors=True)
