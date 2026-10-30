import importlib.util
import json
from pathlib import Path

import pandas as pd
from tourism_dashboard.approved import approved_figure, read_approved, render_approved
from tourism_dashboard.application import create_app


def test_missing_version_displays_message_without_estimates(tmp_path):
    assert read_approved(tmp_path) is None
    children, options = render_approved(tmp_path)
    assert "no disponibles" in children[0].children
    assert options == []


def test_recovery_demonstration_and_execution_records(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts" / "demonstrate_recovery.py"
    spec = importlib.util.spec_from_file_location("recovery_demo", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evidence = module.demonstrate(tmp_path / "demo")
    assert len(evidence["events"]) == 5
    reports = list((tmp_path / "demo/output/reports").glob("execution_*.json"))
    assert len(reports) == 3
    records = [json.loads(path.read_text(encoding="utf-8")) for path in reports]
    assert all(record["started_at"] <= record["finished_at"] for record in records)
    failure = next(record for record in records if record["errors"])
    assert failure["completed_stages"] == ["reading"]
    assert failure["publication"] == "not_attempted"
    assert failure["monitoring"]["quality"]["status"] == "alert"
    assert all(record["publication"] == "published" for record in records if not record["errors"])
    app = create_app(Path(__file__).resolve().parents[1] / "data/arrivals_migration_2009_2026.csv",
                     approved_versions_path=tmp_path / "demo/output/versions")
    key = next(key for key in app.callback_map if "approved-content.children" in key)
    response = app.server.test_client().post("/_dash-update-component", json={
        "output": key,
        "outputs": [{"id": "approved-content", "property": "children"},
                    {"id": "approved-destination", "property": "options"}],
        "inputs": [{"id": "approved-refresh", "property": "n_intervals", "value": 1},
                   {"id": "approved-destination", "property": "value", "value": "Coban"}],
        "state": [], "changedPropIds": ["approved-refresh.n_intervals"],
    })
    assert response.status_code == 200
    body = response.get_json()["response"]
    assert len(body["approved-destination"]["options"]) == 18
    assert "Sin dato" in json.dumps(body)
    assert "MAPE" in json.dumps(body)


def test_gap_is_missing_and_palette_is_consistent():
    observed = pd.DataFrame({"destination": ["Coban", "Coban"], "period": pd.to_datetime(["2025-12-01", "2026-03-01"]), "visitors": [90., 110.]})
    estimates = pd.DataFrame({"destination": ["Coban", "Coban"], "period": pd.to_datetime(["2026-01-01", "2026-02-01"]), "value": [95., 100.]})
    figure = approved_figure(estimates, observed, "Coban")
    assert pd.isna(figure.data[0].y[1:3]).all()
    assert figure.data[0].connectgaps is False
    assert figure.data[0].line.color == "#0B5C8E"
    assert figure.data[1].line.color == "#D55E00"
    assert figure.data[1].line.dash == "dash"
