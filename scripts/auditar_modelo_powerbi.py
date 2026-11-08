"""Contrasta el modelo importado del PBIX con sus CSV, sin ejecutar Desktop.

Dependencia opcional para esta auditoría: pbixray==0.15.5.
La lectura del caché no ejecuta las nuevas medidas de informe ni sus visuales.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from verificar_powerbi import ROOT, require


def audit() -> dict:
    try:
        import numpy as np
        import pandas as pd
        from pbixray import PBIXRay
    except ImportError as exc:
        raise RuntimeError("Instala la dependencia opcional con: python -m pip install pbixray==0.15.5") from exc

    path = ROOT / "powerbi/observatorio_turismo.pbix"
    reader = PBIXRay(str(path))
    tables = {name: reader.get_table(name) for name in (
        "Calendario", "Origenes", "Modelos", "Llegadas", "Hospedaje", "Predicciones", "Metricas", "Observados")}
    predictions = tables["Predicciones"].copy()
    source = pd.read_csv(ROOT / "data/model_predictions_s0.csv")
    def sorted_monthly(frame, keys):
        return frame.assign(date=pd.to_datetime(frame["date"])).sort_values(keys).reset_index(drop=True)

    predictions = sorted_monthly(predictions, ["date", "model_id"])
    source = sorted_monthly(source, ["date", "model_id"])
    for name in ("date", "model_id", "model_label"):
        require(predictions[name].tolist() == source[name].tolist(), f"Cambió {name} en las predicciones importadas.")
    require(np.allclose(predictions[["observed", "estimate"]].astype(float), source[["observed", "estimate"]].astype(float),
                        rtol=1e-12, atol=1e-6), "Las predicciones del PBIX difieren del CSV.")
    arrivals_source = pd.read_csv(ROOT / "data/arrivals_migration_2009_2026.csv", encoding="utf-8-sig")
    arrivals_source = arrivals_source.drop(columns="reported_total").melt(id_vars="date", var_name="origin_key", value_name="arrivals")
    arrivals = tables["Llegadas"].copy()
    arrivals_source = sorted_monthly(arrivals_source, ["date", "origin_key"])
    arrivals = sorted_monthly(arrivals, ["date", "origin_key"])
    require(arrivals["origin_key"].tolist() == arrivals_source["origin_key"].tolist()
            and arrivals["date"].tolist() == arrivals_source["date"].tolist(), "Cambió la clave mes y origen en el PBIX.")
    require(np.allclose(arrivals["arrivals"].astype(float), arrivals_source["arrivals"].astype(float), rtol=1e-12, atol=1e-6), "Las llegadas del PBIX difieren del CSV.")
    require(tables["Observados"]["date"].nunique() == 63, "No hay exactamente 63 meses observados.")
    require(predictions.groupby("date")["observed"].nunique().eq(1).all(), "El observado cambia entre modelos.")
    rows = []
    for metric in tables["Metricas"].itertuples():
        data = predictions[predictions.model_id == metric.model_id]
        error = data.estimate.astype(float) - data.observed.astype(float)
        values = [float(error.abs().mean()), float(np.sqrt((error ** 2).mean())),
                  float((error.abs() / data.observed.astype(float)).mean() * 100)]
        require(np.allclose(values, [metric.mae, metric.rmse, metric.mape], rtol=1e-10, atol=1e-6), "Las métricas importadas no coinciden al recalcular.")
        december = data[data.date == pd.Timestamp("2025-12-01")].iloc[0]
        rows.append({"model_id": metric.model_id, "mae": values[0], "rmse": values[1], "mape_porcentaje": values[2],
                     "observado_diciembre_2025": float(december.observed), "estimado_diciembre_2025": float(december.estimate),
                     "error_diciembre_2025": float(december.estimate - december.observed)})
    with zipfile.ZipFile(path) as pbix:
        model_hash = hashlib.sha256(pbix.read("DataModel")).hexdigest()
    reader.close()
    return {
        "alcance": "Lectura del modelo importado del PBIX con PBIXRay 0.15.5; no ejecución de DAX ni renderizado en Desktop.",
        "filas_tablas_funcionales": {name: len(table) for name, table in tables.items()},
        "predicciones_coinciden_con_csv": True, "llegadas_coinciden_con_csv": True,
        "observado_una_fila_por_mes": True, "sha256_modelo": model_hash, "modelos": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8", newline="\n")
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
