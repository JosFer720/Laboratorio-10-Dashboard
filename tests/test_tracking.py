from __future__ import annotations

from pathlib import Path

import pytest
from mlflow import MlflowClient

from tourism_pipeline.config import load_config
from tourism_pipeline.pipeline import run_pipeline
from tourism_pipeline.synthetic import write_synthetic_sources
from tourism_pipeline.tracking import (
    list_run_records,
    normalize_tracking_uri,
    record_evaluation_metrics,
)
from tourism_pipeline.validation import QualityControlError


def _config(tmp_path: Path, problem: str | None = None):
    data = tmp_path / "data"
    write_synthetic_sources(data, problem=problem)
    return load_config(
        env={
            "INGUAT_DATA_DIR": str(data),
            "PIPELINE_OUTPUT_DIR": str(tmp_path / "output"),
            "MLFLOW_TRACKING_URI": str(tmp_path / "mlruns"),
        }
    )


def _artifact_paths(client: MlflowClient, run_id: str, path: str = "") -> set[str]:
    found: set[str] = set()
    for item in client.list_artifacts(run_id, path):
        if item.is_dir:
            found.update(_artifact_paths(client, run_id, item.path))
        else:
            found.add(item.path.replace("\\", "/"))
    return found


def test_successful_pipeline_run_is_fully_registered(tmp_path: Path) -> None:
    config = _config(tmp_path)

    pipeline_run = run_pipeline(config)

    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    tracked = client.get_run(pipeline_run.tracking_run_id)
    assert tracked.info.status == "FINISHED"
    assert tracked.data.params["pipeline_run_id"] == pipeline_run.run_id
    assert tracked.data.params["git_commit"]
    assert tracked.data.params["source.mobility.sha256"] == pipeline_run.sources["mobility"].sha256
    assert tracked.data.params["source.migration.sha256"] == pipeline_run.sources["migration"].sha256
    assert tracked.data.params["periods.fit"] == "2025-09,2025-10,2025-11,2025-12,2026-03,2026-04,2026-05,2026-06"
    assert tracked.data.params["periods.evaluation"] == "2026-03,2026-04,2026-05,2026-06"
    assert tracked.data.params["procedure.reparto_factor"] == "mean_of_monthly_ratios"
    assert {
        "evaluation.candidate.mae",
        "evaluation.candidate.rmse",
        "evaluation.candidate.mape",
        "evaluation.last_observed.mae",
        "evaluation.historical_mean.mae",
        "evaluation.evaluated_months",
    } <= set(tracked.data.metrics)
    assert tracked.data.tags["pipeline.outcome"] == "success"
    assert tracked.data.tags["acceptance.verdict"] in {"aprobada", "rechazada"}
    artifacts = _artifact_paths(client, pipeline_run.tracking_run_id)
    assert {
        "config/effective_config.json",
        "metadata/sources.json",
        f"quality/quality_{pipeline_run.run_id}.json",
        "outputs/estimates.csv",
        "outputs/reparto_factors.csv",
        "outputs/national_entries.csv",
        "outputs/coverage.csv",
        "outputs/evaluation.csv",
        "outputs/evaluation_by_destination.csv",
        "acceptance/acceptance.json",
    } <= artifacts
    assert all(f"quality.{name}.status" in tracked.data.params for name in (
        "columns_and_types",
        "dates_and_coverage",
        "uniqueness",
        "missing_values",
        "values_and_denominators",
        "methodology",
    ))


def test_critical_failure_is_registered_without_metrics(tmp_path: Path) -> None:
    config = _config(tmp_path, problem="zero_denominator")

    with pytest.raises(QualityControlError):
        run_pipeline(config)

    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    experiment = client.get_experiment_by_name(config.tracking.experiment_name)
    runs = client.search_runs([experiment.experiment_id])
    assert len(runs) == 1
    tracked = runs[0]
    assert tracked.info.status == "FAILED"
    assert tracked.data.metrics == {}
    assert "values_and_denominators" in tracked.data.tags["pipeline.failure_cause"]
    assert any(path.startswith("quality/quality_") for path in _artifact_paths(client, tracked.info.run_id))


def test_evaluation_metrics_hook_logs_only_supplied_values(tmp_path: Path) -> None:
    config = _config(tmp_path)
    pipeline_run = run_pipeline(config)

    record_evaluation_metrics(config, pipeline_run.tracking_run_id, {"mae": 12.5, "rmse": 18.0})

    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    metrics = client.get_run(pipeline_run.tracking_run_id).data.metrics
    assert metrics["mae"] == 12.5
    assert metrics["rmse"] == 18.0


def test_run_query_includes_status_parameters_metrics_and_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    pipeline_run = run_pipeline(config)
    record_evaluation_metrics(config, pipeline_run.tracking_run_id, {"mae": 1.0})

    records = list_run_records(config)

    assert len(records) == 1
    record = records[0]
    assert record["status"] == "FINISHED"
    assert record["parameters"]["pipeline_run_id"] == pipeline_run.run_id
    assert record["metrics"]["mae"] == 1.0
    assert "outputs/estimates.csv" in record["artifacts"]
