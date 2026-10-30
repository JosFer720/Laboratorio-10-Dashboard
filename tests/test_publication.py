from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml
from mlflow import MlflowClient

from tourism_pipeline.cli import EXIT_OK, EXIT_REJECTED
from tourism_pipeline.cli import main as run_main
from tourism_pipeline.config import DEFAULT_CONFIG_PATH, load_config
from tourism_pipeline.pipeline import run_pipeline
from tourism_pipeline.publication import (
    CURRENT_FILE,
    PublicationError,
    current_version,
    list_versions,
    publish_version,
    read_history,
    restore_version,
)
from tourism_pipeline.restore import main as restore_main
from tourism_pipeline.synthetic import write_synthetic_sources
from tourism_pipeline.tracking import normalize_tracking_uri


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    write_synthetic_sources(tmp_path / "data")
    return {
        "INGUAT_DATA_DIR": str(tmp_path / "data"),
        "PIPELINE_OUTPUT_DIR": str(tmp_path / "output"),
        "MLFLOW_TRACKING_URI": str(tmp_path / "mlflow"),
        "PIPELINE_VERSIONS_DIR": str(tmp_path / "versions"),
    }


def _strict_config_file(tmp_path: Path) -> Path:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["acceptance"]["max_mape"] = 0.1
    path = tmp_path / "strict.yaml"
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    return path


def test_approved_candidate_is_published_as_current_version(env):
    config = load_config(env=env)

    run = run_pipeline(config)

    assert run.acceptance.approved
    assert run.published is not None
    current = current_version(config.publication.versions_dir)
    assert current.version_id == run.run_id
    assert {
        "estimates.csv",
        "reparto_factors.csv",
        "national_entries.csv",
        "coverage.csv",
        "evaluation.csv",
        "evaluation_by_destination.csv",
        "effective_config.json",
        "metadata.json",
    } <= {path.name for path in current.path.iterdir()}
    metadata = current.metadata
    assert metadata["run_id"] == run.run_id
    assert metadata["procedure_version"] == "1"
    assert metadata["validation"]["metric"] == "MAPE"
    assert metadata["validation"]["evaluated_periods"] == ["2026-03", "2026-04", "2026-05", "2026-06"]
    assert metadata["acceptance"]["verdict"] == "aprobada"
    estimates = pd.read_csv(current.file("estimates.csv"))
    assert set(estimates["run_id"]) == {run.run_id}


def test_rejected_candidate_leaves_the_current_version_untouched(env, tmp_path):
    first = run_pipeline(load_config(env=env))
    pointer = Path(env["PIPELINE_VERSIONS_DIR"]) / CURRENT_FILE
    before = pointer.read_bytes()

    code = run_main(["--config", str(_strict_config_file(tmp_path))], env=env)

    assert code == EXIT_REJECTED
    assert pointer.read_bytes() == before
    assert current_version(env["PIPELINE_VERSIONS_DIR"]).version_id == first.run_id
    assert len(list_versions(env["PIPELINE_VERSIONS_DIR"])) == 1


def test_rejection_is_recorded_in_mlflow_and_in_the_run_report(env, tmp_path):
    config = load_config(_strict_config_file(tmp_path), env=env)

    run = run_pipeline(config)

    assert not run.acceptance.approved
    assert run.published is None
    assert run.current is None
    tracked = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri)).get_run(
        run.tracking_run_id
    )
    assert tracked.data.tags["acceptance.verdict"] == "rechazada"
    assert tracked.data.tags["publication.outcome"] == "not_published"
    assert tracked.data.tags["publication.current_version"] == "none"
    assert tracked.data.metrics["evaluation.candidate.mape"] > 0.1
    report = json.loads(
        (config.paths.reports_path / f"acceptance_{run.run_id}.json").read_text(encoding="utf-8")
    )
    assert report["verdict"] == "rechazada"
    assert report["evaluation"]["evaluated_periods"][0] == "2026-03"


def test_new_approved_version_keeps_the_previous_one(env):
    config = load_config(env=env)
    first = run_pipeline(config)
    second = run_pipeline(config)

    versions = [version.version_id for version in list_versions(config.publication.versions_dir)]

    assert versions == [first.run_id, second.run_id]
    assert current_version(config.publication.versions_dir).version_id == second.run_id


def test_restore_command_brings_back_a_previous_version_and_records_it(env, capsys):
    config = load_config(env=env)
    first = run_pipeline(config)
    run_pipeline(config)

    code = restore_main(["--version", first.run_id], env=env)

    assert code == EXIT_OK
    assert current_version(config.publication.versions_dir).version_id == first.run_id
    last = read_history(config.publication.versions_dir)[-1]
    assert last["action"] == "restore"
    assert last["version"] == first.run_id
    tracked = MlflowClient(tracking_uri=normalize_tracking_uri(config.tracking.uri)).get_run(
        first.tracking_run_id
    )
    assert tracked.data.tags["publication.restored_at"] == last["at"]
    assert restore_main([], env=env) == EXIT_OK
    listing = capsys.readouterr().out
    assert f"* {first.run_id}" in listing


def test_restoring_an_unknown_version_changes_nothing(env):
    config = load_config(env=env)
    run = run_pipeline(config)

    assert restore_main(["--version", "no-existe"], env=env) == 1
    assert current_version(config.publication.versions_dir).version_id == run.run_id
    with pytest.raises(PublicationError, match="No existe"):
        restore_version(config.publication.versions_dir, "no-existe")


def test_only_approved_versions_can_be_published(tmp_path):
    estimates = tmp_path / "estimates.csv"
    estimates.write_text("destination,value\nCoban,1\n", encoding="utf-8")

    with pytest.raises(PublicationError, match="aprobadas"):
        publish_version(
            tmp_path / "versions",
            "run-x",
            {"results": estimates},
            {"acceptance": {"approved": False}},
        )
    assert current_version(tmp_path / "versions") is None


def test_publishing_leaves_no_temporary_files(env):
    config = load_config(env=env)
    run_pipeline(config)

    leftovers = [
        path.name
        for path in Path(config.publication.versions_dir).iterdir()
        if path.name.startswith(".")
    ]

    assert leftovers == []


def test_reproducibility_check_never_publishes(env):
    from tourism_pipeline.reproducibility import check_reproducibility

    config = load_config(env=env)
    check_reproducibility(config)

    assert current_version(config.publication.versions_dir) is None
