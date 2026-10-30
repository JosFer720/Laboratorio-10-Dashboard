"""Monitoreo operativo; las alertas no se interpretan como error predictivo."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd


def _months(values):
    return sorted(set(pd.DatetimeIndex(pd.to_datetime(values, errors="coerce")).dropna().strftime("%Y-%m")))


def source_snapshot(mobility, migration, config):
    snapshots = {}
    for name, frame, key in (
        ("mobility", mobility, config.quality.mobility_key),
        ("migration", migration, config.quality.migration_key),
    ):
        if name == "mobility":
            dates = pd.to_datetime(frame.get("fecha", pd.Series(dtype=str)), errors="coerce", format="mixed")
        else:
            dates = pd.to_datetime(pd.DataFrame({
                "year": frame.get("Año", pd.Series(dtype=float)),
                "month": frame.get("Mes cod", pd.Series(dtype=float)), "day": 1,
            }), errors="coerce")
        columns = config.quality.mobility_columns if name == "mobility" else config.quality.migration_columns
        missing = frame.reindex(columns=columns).isna()
        snapshots[name] = {
            "rows": len(frame), "missing_fraction": float(missing.to_numpy().mean()) if len(frame) else 1.0,
            "duplicates": int(frame.duplicated(list(key)).sum()) if set(key) <= set(frame.columns) else None,
            "months": _months(dates),
        }
    return snapshots


def check_monitoring(snapshot, estimates, config, previous_snapshot=None, previous_estimates=None):
    freshness, quality, results = [], [], []
    for name, expected in (("mobility", config.periods.mobility_coverage),
                           ("migration", config.periods.migration_coverage)):
        latest = max(expected).strftime("%Y-%m")
        months = snapshot[name]["months"]
        if not months or max(months) != latest:
            freshness.append(f"{name}: último mes recibido distinto del esperado {latest}.")
        if previous_snapshot and name in previous_snapshot:
            before, after = previous_snapshot[name], snapshot[name]
            if abs(after["missing_fraction"] - before["missing_fraction"]) > config.monitoring.max_missing_fraction_change:
                quality.append(f"{name}: cambio de faltantes superior al umbral.")
            if after["duplicates"] != before["duplicates"]:
                quality.append(f"{name}: cambió la cantidad de claves duplicadas.")
            if after["months"] != before["months"]:
                quality.append(f"{name}: cambió la cobertura recibida.")
    if estimates is not None:
        expected = max(config.periods.estimate).strftime("%Y-%m")
        months = _months(estimates["period"])
        if not months or max(months) != expected:
            freshness.append(f"Resultados: último mes distinto del esperado {expected}.")
        values = estimates["value"].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            results.append("Estimaciones negativas o no finitas.")
        if previous_estimates is not None:
            keys = ["destination", "period"]
            left, right = estimates.copy(), previous_estimates.copy()
            for frame in (left, right):
                frame["period"] = pd.to_datetime(frame["period"])
            joined = left.merge(right, on=keys, suffixes=("", "_previous"), validate="one_to_one")
            before = joined["value_previous"].to_numpy(dtype=float)
            difference = abs(joined["value"].to_numpy(dtype=float) - before)
            fraction = np.divide(difference, abs(before), out=np.full_like(difference, np.inf), where=before != 0)
            fraction[(before == 0) & (difference == 0)] = 0
            if (fraction > config.monitoring.max_estimate_change_fraction).any():
                results.append("Variación alta frente a la versión vigente: requiere revisión; no demuestra pérdida de precisión.")
    return {
        "freshness": {"status": "alert" if freshness else "ok", "alerts": freshness},
        "quality": {"status": "alert" if quality else ("ok" if previous_snapshot else "no_baseline"), "alerts": quality},
        "results": {"status": "not_evaluated" if estimates is None else ("alert" if results else "ok"), "alerts": results},
    }


class ExecutionRecord:
    def __init__(self, config, run_id, started_at):
        self.path = config.paths.reports_path / f"execution_{run_id}.json"
        self.previous = None
        candidates = sorted(config.paths.reports_path.glob("execution_*.json"), key=lambda path: path.stat().st_mtime_ns)
        for path in reversed(candidates):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("source_snapshot"):
                self.previous = record["source_snapshot"]
                break
        self.data = {"run_id": run_id, "started_at": started_at.isoformat(), "finished_at": None,
                     "completed_stages": [], "warnings": [], "errors": [], "publication": "not_attempted"}

    def completed(self, name):
        self.data["completed_stages"].append(name)

    def write(self):
        self.data["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        return self.path
