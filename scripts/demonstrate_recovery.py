"""Demostración repetible exclusivamente con fuentes sintéticas aisladas."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tourism_dashboard.approved import read_approved, render_approved
from tourism_pipeline.config import load_config
from tourism_pipeline.pipeline import run_pipeline
from tourism_pipeline.restore import main as restore_main
from tourism_pipeline.synthetic import write_synthetic_sources
from tourism_pipeline.tracking import list_run_records
from tourism_pipeline.validation import QualityControlError


def demonstrate(workspace):
    workspace = Path(workspace).resolve()
    # Una carpeta nueva evita sobrescribir fuentes o registros de otra ejecución.
    workspace.mkdir(parents=True, exist_ok=False)
    env = {"INGUAT_DATA_DIR": str(workspace / "sources"), "PIPELINE_OUTPUT_DIR": str(workspace / "output")}
    config = load_config(env=env)
    store = config.publication.versions_dir
    events = []

    def record(step, **details):
        events.append({"step": step, **details})

    assert read_approved(store) is None
    assert render_approved(store)[1] == []
    record("without_approved_version", estimates_available=False)
    write_synthetic_sources(config.paths.data_dir)
    first = run_pipeline(config)
    assert first.published is not None
    assert read_approved(store)[0].version_id == first.run_id
    assert render_approved(store)[1]
    record("published", version=first.run_id, mape=first.evaluation.metrics["candidate"]["mape"])
    first_bytes = read_approved(store)[1].to_csv(index=False)

    write_synthetic_sources(config.paths.data_dir, problem="duplicate_row")
    try:
        run_pipeline(config)
    except QualityControlError as exc:
        failed = next(run for run in list_run_records(config) if run["parameters"]["pipeline_run_id"] == exc.report.run_id)
        assert failed["status"] == "FAILED"
        assert "uniqueness" in failed["tags"]["pipeline.failure_cause"]
        assert not failed["metrics"]
        assert read_approved(store)[0].version_id == first.run_id
        assert read_approved(store)[1].to_csv(index=False) == first_bytes
        assert render_approved(store)[1]
        record("detected_failure", run=exc.report.run_id, tracking_run_id=failed["tracking_run_id"],
               status=failed["status"], cause=failed["tags"]["pipeline.failure_cause"],
               approved_version_preserved=first.run_id, dashboard_available=True)
    else:
        raise AssertionError("El duplicado no fue detectado.")

    write_synthetic_sources(config.paths.data_dir)
    recovered = run_pipeline(config)
    assert recovered.published is not None
    assert read_approved(store)[0].version_id == recovered.run_id
    record("recovered_and_published", version=recovered.run_id)
    assert restore_main(["--version", first.run_id], env=env) == 0
    assert read_approved(store)[0].version_id == first.run_id
    assert read_approved(store)[1].to_csv(index=False) == first_bytes
    assert render_approved(store)[1]
    record("restored_and_read_by_dashboard", version=first.run_id)
    evidence = {"synthetic_only": True, "events": events, "runs": list_run_records(config)}
    target = workspace / "evidence.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"events": events, "evidence": str(target)}, ensure_ascii=False, indent=2))
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, help="Carpeta nueva para datos sintéticos, MLflow y evidencia.")
    demonstrate(parser.parse_args().workspace)
