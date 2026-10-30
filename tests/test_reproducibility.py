from __future__ import annotations

from pathlib import Path
from dataclasses import replace

from mlflow import MlflowClient

from tourism_pipeline.config import load_config
from tourism_pipeline.reproducibility import check_reproducibility
from tourism_pipeline.synthetic import write_synthetic_sources
from tourism_pipeline.tracking import normalize_tracking_uri


def test_reproducibility_runs_twice_and_registers_equivalence(tmp_path: Path) -> None:
    data = tmp_path / "data"
    write_synthetic_sources(data)
    config = load_config(
        env={
            "INGUAT_DATA_DIR": str(data),
            "PIPELINE_OUTPUT_DIR": str(tmp_path / "output"),
            "MLFLOW_TRACKING_URI": str(tmp_path / "mlruns"),
        }
    )

    result = check_reproducibility(config)

    assert result.equivalent
    assert result.max_absolute_difference == 0.0
    assert result.tolerance == config.tracking.reproducibility_tolerance
    assert set(result.compared_files) == {
        "estimates.csv",
        "reparto_factors.csv",
        "national_entries.csv",
        "coverage.csv",
        "evaluation.csv",
        "evaluation_by_destination.csv",
    }
    client = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri))
    for run_id in result.tracking_run_ids:
        tracked = client.get_run(run_id)
        assert tracked.data.tags["reproducibility.equivalent"] == "true"
        assert tracked.data.metrics["reproducibility.max_absolute_difference"] == 0.0


def test_reproducibility_tolerance_comes_from_configuration(tmp_path: Path) -> None:
    data = tmp_path / "data"
    write_synthetic_sources(data)
    config = load_config(
        env={
            "INGUAT_DATA_DIR": str(data),
            "PIPELINE_OUTPUT_DIR": str(tmp_path / "output"),
            "MLFLOW_TRACKING_URI": str(tmp_path / "mlruns"),
            "PIPELINE_REPRODUCIBILITY_TOLERANCE": "0.00001",
        }
    )

    result = check_reproducibility(config)

    assert result.tolerance == 0.00001


def test_reproducibility_uses_configured_output_names(tmp_path: Path) -> None:
    data = tmp_path / "data"
    write_synthetic_sources(data)
    config = load_config(
        env={
            "INGUAT_DATA_DIR": str(data),
            "PIPELINE_OUTPUT_DIR": str(tmp_path / "output"),
            "MLFLOW_TRACKING_URI": str(tmp_path / "mlruns"),
        }
    )
    config = replace(
        config,
        paths=replace(config.paths, results_file="custom_estimates.csv"),
    )

    result = check_reproducibility(config)

    assert result.equivalent
    assert "custom_estimates.csv" in result.compared_files
