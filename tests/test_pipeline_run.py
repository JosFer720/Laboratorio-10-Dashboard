from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from tourism_pipeline.cli import EXIT_CONTROL_FAILED, EXIT_OK, EXIT_SETUP_ERROR, main
from tourism_pipeline.config import load_config
from tourism_pipeline.pipeline import STAGING_PREFIX, run_pipeline
from tourism_pipeline.synthetic import PROBLEMS, write_synthetic_sources


ROOT = Path(__file__).resolve().parents[1]
RESULT_FILES = ("estimates.csv", "reparto_factors.csv", "national_entries.csv", "coverage.csv")
ENVIRONMENT_KEYS = ("SYSTEMROOT", "PATH", "TEMP", "TMP", "HOME", "USERPROFILE", "LANG")


def _env(data_dir: Path, output_dir: Path) -> dict[str, str]:
    return {"INGUAT_DATA_DIR": str(data_dir), "PIPELINE_OUTPUT_DIR": str(output_dir)}


def _snapshot(output: Path) -> dict[str, bytes]:
    return {name: (output / name).read_bytes() for name in RESULT_FILES}


def _staging_leftovers(output: Path) -> list[Path]:
    return [path for path in output.iterdir() if path.name.startswith(STAGING_PREFIX)]


@pytest.fixture
def workspace(tmp_path: Path) -> dict[str, Path]:
    return {"data": tmp_path / "data", "output": tmp_path / "output", "tmp": tmp_path}


def test_healthy_run_writes_results_report_and_leaves_no_staging(workspace) -> None:
    write_synthetic_sources(workspace["data"])
    config = load_config(env=_env(workspace["data"], workspace["output"]))

    run = run_pipeline(config)

    output = workspace["output"]
    assert set(run.files) == {"results", "factors", "national_series", "coverage"}
    assert all((output / name).is_file() for name in RESULT_FILES)
    assert (output / "reports" / f"quality_{run.run_id}.json").is_file()
    assert not _staging_leftovers(output)
    assert not run.quality_report.has_critical_failures
    assert set(run.sources) == {"mobility", "migration"}
    assert all(len(item.sha256) == 64 for item in run.sources.values())

    results = pd.read_csv(output / "estimates.csv")
    assert set(results["run_id"]) == {run.run_id}
    assert set(results["period"]) == {"2026-01-01", "2026-02-01"}
    assert results["destination"].nunique() == 18
    assert results["value"].notna().all()
    assert (results["value"] > 0).all()


def test_uncovered_months_are_never_filled_with_zero(workspace) -> None:
    write_synthetic_sources(workspace["data"])
    config = load_config(env=_env(workspace["data"], workspace["output"]))

    run_pipeline(config)

    coverage = pd.read_csv(workspace["output"] / "coverage.csv")
    gap = coverage.loc[coverage["period"].isin(["2026-01-01", "2026-02-01"])]
    assert not gap["mobility"].any()
    assert set(gap["status"]) == {"solo entradas nacionales"}


def test_two_runs_with_same_data_give_same_estimates(workspace) -> None:
    write_synthetic_sources(workspace["data"])
    config = load_config(env=_env(workspace["data"], workspace["output"]))

    first = run_pipeline(config)
    first_results = pd.read_csv(workspace["output"] / "estimates.csv")
    second = run_pipeline(config)
    second_results = pd.read_csv(workspace["output"] / "estimates.csv")

    assert first.run_id != second.run_id
    assert first.sources == second.sources
    columns = ["destination", "destination_group", "period", "value", "unit", "kind"]
    pd.testing.assert_frame_equal(first_results[columns], second_results[columns])


@pytest.mark.parametrize("problem", PROBLEMS)
def test_critical_problem_stops_without_touching_previous_results(workspace, problem) -> None:
    write_synthetic_sources(workspace["data"])
    write_synthetic_sources(workspace["tmp"] / "broken", problem=problem)
    output = workspace["output"]
    assert main([], env=_env(workspace["data"], output)) == EXIT_OK
    before = _snapshot(output)

    code = main([], env=_env(workspace["tmp"] / "broken", output))

    assert code == EXIT_CONTROL_FAILED
    assert _snapshot(output) == before
    assert not _staging_leftovers(output)
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in (output / "reports").glob("quality_*.json")
    ]
    assert sum(report["has_critical_failures"] for report in reports) == 1


def test_first_run_with_problem_creates_no_results(workspace) -> None:
    write_synthetic_sources(workspace["data"], problem="zero_denominator")
    output = workspace["output"]

    code = main([], env=_env(workspace["data"], output))

    assert code == EXIT_CONTROL_FAILED
    assert not any((output / name).exists() for name in RESULT_FILES)
    assert list((output / "reports").glob("quality_*.json"))


def test_fixing_the_problem_and_running_again_publishes(workspace) -> None:
    write_synthetic_sources(workspace["data"], problem="duplicate_row")
    output = workspace["output"]
    env = _env(workspace["data"], output)
    assert main([], env=env) == EXIT_CONTROL_FAILED

    write_synthetic_sources(workspace["data"])

    assert main([], env=env) == EXIT_OK
    assert (output / "estimates.csv").is_file()


def test_missing_data_directory_is_a_setup_error(workspace) -> None:
    code = main([], env={"PIPELINE_OUTPUT_DIR": str(workspace["output"])})

    assert code == EXIT_SETUP_ERROR


def test_missing_source_file_is_a_setup_error(workspace) -> None:
    workspace["data"].mkdir()

    code = main([], env=_env(workspace["data"], workspace["output"]))

    assert code == EXIT_SETUP_ERROR
    assert not (workspace["output"] / "estimates.csv").exists()


def test_documented_command_runs_from_a_clean_process(workspace) -> None:
    write_synthetic_sources(workspace["data"])
    env = {key: os.environ[key] for key in ENVIRONMENT_KEYS if key in os.environ}
    env.update(_env(workspace["data"], workspace["output"]))

    completed = subprocess.run(
        [sys.executable, "run_pipeline.py"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )

    assert completed.returncode == EXIT_OK, completed.stdout + completed.stderr
    assert "terminada" in completed.stdout
    assert (workspace["output"] / "estimates.csv").is_file()
