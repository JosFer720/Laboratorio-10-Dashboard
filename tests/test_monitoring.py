import numpy as np
import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.monitoring import check_monitoring, source_snapshot
from tourism_pipeline.synthetic import build_mobility, build_migration


@pytest.fixture
def monitoring_data(tmp_path):
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})
    mobility = pd.concat([frame.assign(sheet=sheet) for sheet, frame in build_mobility().items()])
    snapshot = source_snapshot(mobility, build_migration(), config)
    estimates = pd.DataFrame({"destination": ["Coban", "Coban"], "period": ["2026-01-01", "2026-02-01"], "value": [100., 110.]})
    return config, mobility, snapshot, estimates


def test_freshness_uses_configured_coverage_not_today(monitoring_data):
    config, _, snapshot, estimates = monitoring_data
    assert check_monitoring(snapshot, estimates, config)["freshness"]["status"] == "ok"
    snapshot["mobility"]["months"].remove("2026-08")
    snapshot["migration"]["months"].remove("2026-06")
    result = check_monitoring(snapshot, estimates.iloc[:1], config)
    assert len(result["freshness"]["alerts"]) == 3


def test_quality_compares_missing_duplicates_and_coverage(monitoring_data):
    config, mobility, previous, estimates = monitoring_data
    mobility = mobility.loc[mobility.fecha.ne(pd.Timestamp("2026-08-01"))].copy()
    mobility["pais"] = None
    mobility = pd.concat([mobility, mobility.iloc[:1]])
    snapshot = source_snapshot(mobility, build_migration(), config)
    result = check_monitoring(snapshot, estimates, config, previous)
    assert len(result["quality"]["alerts"]) == 3


@pytest.mark.parametrize("value", [-1, np.inf, np.nan])
def test_invalid_estimates_raise_alert(monitoring_data, value):
    config, _, snapshot, estimates = monitoring_data
    estimates.loc[0, "value"] = value
    assert check_monitoring(snapshot, estimates, config)["results"]["status"] == "alert"


def test_variation_is_alert_and_zero_baseline_is_explicit(monitoring_data):
    config, _, snapshot, estimates = monitoring_data
    previous = estimates.copy()
    previous["value"] = 0.
    checks = check_monitoring(snapshot, estimates, config, previous_estimates=previous)
    assert "no demuestra" in checks["results"]["alerts"][0]
    previous["value"] = estimates["value"]
    assert check_monitoring(snapshot, estimates, config, previous_estimates=previous)["results"]["status"] == "ok"


def test_first_run_and_early_failure_do_not_invent_checks(monitoring_data):
    config, _, snapshot, _ = monitoring_data
    checks = check_monitoring(snapshot, None, config)
    assert checks["results"]["status"] == "not_evaluated"
    assert checks["quality"]["status"] == "no_baseline"
