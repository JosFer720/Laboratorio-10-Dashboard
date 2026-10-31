from __future__ import annotations

import os
import subprocess
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from mlflow import MlflowClient

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.ingestion import FileFingerprint
from tourism_pipeline.validation import QualityReport


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DESCRIPTIONS = {
    "mobility": "Base mensual de movilidad por subdestino",
    "migration": "Entradas nacionales de la base de migración",
}


def normalize_tracking_uri(uri: str) -> str:
    if "://" in uri or uri.startswith("sqlite:"):
        return uri
    path = Path(uri).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(path / 'mlflow.db').as_posix()}"


def _artifact_root(uri: str) -> str | None:
    if "://" in uri or uri.startswith("sqlite:"):
        return None
    path = Path(uri).expanduser().resolve() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path.as_uri()


def _month_list(values: tuple[pd.Timestamp, ...]) -> str:
    return ",".join(f"{value:%Y-%m}" for value in values)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    return value


def effective_config(config: PipelineConfig) -> dict[str, Any]:
    """Configuración usada en la ejecución, sin la ruta de los datos institucionales."""
    effective = _jsonable(config)
    effective["paths"]["data_dir"] = "<configured outside the repository>"
    return effective


def git_commit() -> str:
    """Identificador del commit del código.

    Dentro de un contenedor no hay repositorio ni `git`: ahí se toma de la
    variable de entorno `GIT_COMMIT`.
    """
    declared = os.environ.get("GIT_COMMIT", "").strip()
    if declared and declared != "unknown":
        return declared
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={REPOSITORY_ROOT.as_posix()}", "rev-parse", "HEAD"],
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


class RunTracker:
    def __init__(
        self, config: PipelineConfig, pipeline_run_id: str, generated_at: datetime
    ) -> None:
        self.config = config
        self.client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
        experiment = self.client.get_experiment_by_name(config.tracking.experiment_name)
        experiment_id = (
            experiment.experiment_id
            if experiment is not None
            else self.client.create_experiment(
                config.tracking.experiment_name,
                artifact_location=_artifact_root(config.tracking.uri),
            )
        )
        run = self.client.create_run(
            experiment_id,
            run_name=pipeline_run_id,
            tags={
                "pipeline.run_id": pipeline_run_id,
                "pipeline.generated_at": generated_at.isoformat(timespec="seconds"),
            },
        )
        self.run_id = run.info.run_id
        self._log_initial(pipeline_run_id, generated_at)

    def _log_initial(self, pipeline_run_id: str, generated_at: datetime) -> None:
        params = {
            "pipeline_run_id": pipeline_run_id,
            "generated_at": generated_at.isoformat(timespec="seconds"),
            "git_commit": git_commit(),
            "procedure.version": self.config.parameters.procedure_version,
            "procedure.unit": self.config.parameters.unit,
            "procedure.seed": self.config.parameters.seed,
            "procedure.reparto_factor": self.config.parameters.reparto_factor,
            "migration.traveler_types": ",".join(self.config.parameters.migration.traveler_types),
            "migration.first_year": self.config.parameters.migration.first_year,
            "periods.fit": _month_list(self.config.periods.fit),
            "periods.evaluation": _month_list(self.config.periods.evaluation),
            "periods.estimate": _month_list(self.config.periods.estimate),
            "reproducibility.tolerance": self.config.tracking.reproducibility_tolerance,
        }
        for key, value in params.items():
            self.client.log_param(self.run_id, key, value)
        self.client.log_dict(
            self.run_id, effective_config(self.config), "config/effective_config.json"
        )

    def log_sources(self, sources: Mapping[str, FileFingerprint]) -> None:
        records = {}
        for name, fingerprint in sources.items():
            self.client.log_param(self.run_id, f"source.{name}.file_name", fingerprint.file_name)
            self.client.log_param(self.run_id, f"source.{name}.size_bytes", fingerprint.size_bytes)
            self.client.log_param(self.run_id, f"source.{name}.sha256", fingerprint.sha256)
            records[name] = {
                **asdict(fingerprint),
                "description": SOURCE_DESCRIPTIONS.get(name, name),
            }
        self.client.log_dict(self.run_id, records, "metadata/sources.json")

    def log_quality(self, report: QualityReport) -> None:
        self.client.set_tag(
            self.run_id, "quality.has_critical_failures", str(report.has_critical_failures).lower()
        )
        for result in report.results:
            self.client.log_param(self.run_id, f"quality.{result.name}.status", result.status.value)
        if report.path and report.path.is_file():
            self.client.log_artifact(self.run_id, str(report.path), artifact_path="quality")

    def log_outputs(self, files: Mapping[str, Path]) -> None:
        for path in files.values():
            self.client.log_artifact(self.run_id, str(path), artifact_path="outputs")

    def log_acceptance(self, decision: Mapping[str, Any], evaluated_months: str) -> None:
        self.client.log_param(self.run_id, "evaluation.months", evaluated_months)
        for name, value in decision["thresholds"].items():
            self.client.log_param(self.run_id, f"acceptance.{name}", value)
        self.client.set_tag(self.run_id, "acceptance.verdict", decision["verdict"])
        if decision["reasons"]:
            self.client.set_tag(self.run_id, "acceptance.reasons", " | ".join(decision["reasons"]))
        self.client.log_dict(self.run_id, dict(decision), "acceptance/acceptance.json")

    def log_publication(self, published_version: str | None, current_version: str | None) -> None:
        outcome = "published" if published_version else "not_published"
        self.client.set_tag(self.run_id, "publication.outcome", outcome)
        self.client.set_tag(self.run_id, "publication.current_version", current_version or "none")

    def finish(self) -> None:
        self.client.set_tag(self.run_id, "pipeline.outcome", "success")
        self.client.set_terminated(self.run_id, status="FINISHED", end_time=int(time.time() * 1000))

    def fail(self, cause: str) -> None:
        self.client.set_tag(self.run_id, "pipeline.outcome", "failed")
        self.client.set_tag(self.run_id, "pipeline.failure_cause", cause)
        self.client.set_terminated(self.run_id, status="FAILED", end_time=int(time.time() * 1000))


def record_evaluation_metrics(
    config: PipelineConfig, tracking_run_id: str, metrics: Mapping[str, float]
) -> None:
    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    for name, value in metrics.items():
        client.log_metric(tracking_run_id, name, float(value))


def record_restoration(
    config: PipelineConfig, tracking_run_id: str, restored_at: str
) -> None:
    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    client.set_tag(tracking_run_id, "publication.restored_at", restored_at)


def _artifact_paths(client: MlflowClient, run_id: str, path: str = "") -> list[str]:
    paths: list[str] = []
    for item in client.list_artifacts(run_id, path):
        if item.is_dir:
            paths.extend(_artifact_paths(client, run_id, item.path))
        else:
            paths.append(item.path.replace("\\", "/"))
    return sorted(paths)


def list_run_records(config: PipelineConfig, limit: int = 20) -> list[dict[str, Any]]:
    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    experiment = client.get_experiment_by_name(config.tracking.experiment_name)
    if experiment is None:
        return []
    runs = client.search_runs(
        [experiment.experiment_id], max_results=limit, order_by=["attributes.start_time DESC"]
    )
    return [
        {
            "tracking_run_id": run.info.run_id,
            "status": run.info.status,
            "parameters": dict(run.data.params),
            "metrics": dict(run.data.metrics),
            "tags": dict(run.data.tags),
            "artifacts": _artifact_paths(client, run.info.run_id),
        }
        for run in runs
    ]


def record_reproducibility(
    config: PipelineConfig,
    run_ids: tuple[str, str],
    equivalent: bool,
    max_absolute_difference: float,
) -> None:
    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    for run_id in run_ids:
        client.set_tag(run_id, "reproducibility.equivalent", str(equivalent).lower())
        client.log_metric(
            run_id, "reproducibility.max_absolute_difference", max_absolute_difference
        )
