"""Comprueba las fuentes de referencia y la estructura del proyecto de Power BI.

No ejecuta Power Query, DAX ni Power BI Desktop. Los resultados son controles
de las fuentes y de la definición, no evidencia de actualización del informe.
Solo requiere la biblioteca estándar de Python.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import re
import subprocess
from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = "29a091d26d8a9efec62e4ea292a3b5240fddee17"
FILES = (
    "arrivals_migration_2009_2026.csv",
    "hotel_occupancy_inguat_2022_2024.csv",
    "model_predictions_s0.csv",
    "model_metrics_s0.csv",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def reference_file(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{REFERENCE}:{path}"], cwd=ROOT,
        check=True, capture_output=True,
    ).stdout


def reference_metadata() -> tuple[dict, dict]:
    tree = ast.parse(reference_file("src/tourism_dashboard/data.py").decode("utf-8"))
    constants = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"ORIGIN_METADATA", "MODEL_LABELS"}:
                    constants[target.id] = ast.literal_eval(node.value)
    return constants["ORIGIN_METADATA"], constants["MODEL_LABELS"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def number(value: str) -> Decimal:
    result = Decimal(value)
    require(result.is_finite() and result >= 0, "Valor no finito o negativo en la fuente.")
    return result


def close(actual: Decimal, expected: Decimal) -> bool:
    return abs(actual - expected) <= Decimal("0.000001") + abs(expected) * Decimal("1e-10")


def monthly_dates(start: date, count: int) -> list[str]:
    months = start.year * 12 + start.month - 1
    return [date((months + i) // 12, (months + i) % 12 + 1, 1).isoformat() for i in range(count)]


def validate_definition(project_dir: Path, origins: dict) -> dict:
    model = json.loads((project_dir / "observatorio_turismo.SemanticModel/model.bim").read_text(encoding="utf-8"))["model"]
    tables = {table["name"]: table for table in model["tables"]}
    expected_tables = {"Calendario", "Origenes", "Modelos", "Llegadas", "Hospedaje", "Predicciones", "Metricas", "Observados"}
    require(set(tables) == expected_tables, "Las tablas no coinciden con el modelo documentado.")
    expected_relations = {
        ("Llegadas", "date", "Calendario", "date"),
        ("Hospedaje", "date", "Calendario", "date"),
        ("Predicciones", "date", "Calendario", "date"),
        ("Observados", "date", "Calendario", "date"),
        ("Llegadas", "origin_key", "Origenes", "origin_key"),
        ("Predicciones", "model_id", "Modelos", "model_id"),
        ("Metricas", "model_id", "Modelos", "model_id"),
    }
    actual_relations = set()
    for relation in model["relationships"]:
        require(relation.get("isActive", True), "Hay una relación inactiva.")
        require(relation["crossFilteringBehavior"] == "oneDirection", "No se admiten filtros bidireccionales.")
        require((relation["fromCardinality"], relation["toCardinality"]) == ("many", "one"), "La cardinalidad debe ser muchos a uno.")
        key = tuple(relation[name] for name in ("fromTable", "fromColumn", "toTable", "toColumn"))
        for table, column in ((key[0], key[1]), (key[2], key[3])):
            require(column in {c["name"] for c in tables[table]["columns"]}, f"Columna inexistente: {table}[{column}].")
        actual_relations.add(key)
    require(actual_relations == expected_relations and len(model["relationships"]) == 7, "Hay relaciones faltantes, repetidas o adicionales.")
    for table in tables.values():
        columns = {c["name"] for c in table["columns"]}
        for column in table["columns"]:
            if "sortByColumn" in column:
                require(column["sortByColumn"] in columns, "Orden de columna inválido.")
        require(all(p["mode"] == "import" for p in table["partitions"]), "Se esperaba modo de importación.")
    observed = next(c for c in tables["Predicciones"]["columns"] if c["name"] == "observed")
    require(observed.get("isHidden") and observed["summarizeBy"] == "none", "El observado repetido no debe ofrecer suma implícita.")
    require(tables["Calendario"].get("dataCategory") == "Time", "Falta marcar el calendario como tabla de fechas.")
    date_column = next(c for c in tables["Calendario"]["columns"] if c["name"] == "date")
    require(date_column.get("isKey"), "La fecha del calendario debe ser única.")
    expression = next(e for e in model["expressions"] if e["name"] == "CatalogoOrigenes")
    actual_origins = {}
    for line in expression["expression"]:
        match = re.match(r'^\s*\{(".*"), (\d+)\},?\s*$', line)
        if match:
            row = next(csv.reader(io.StringIO(match[1]), skipinitialspace=True))
            actual_origins[row[0]] = tuple(row[1:])
    require(actual_origins == origins, "La clasificación de mercados cambió respecto del Laboratorio 10.")
    report = project_dir / "observatorio_turismo.Report"
    definition = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
    target = (report / definition["datasetReference"]["byPath"]["path"]).resolve()
    require(target == (project_dir / "observatorio_turismo.SemanticModel").resolve(), "El informe apunta a otro modelo.")
    theme = report / "StaticResources/RegisteredResources/tema_observatorio.json"
    require(theme.read_bytes() == (project_dir / "tema_observatorio.json").read_bytes(), "El tema incrustado difiere del tema de referencia.")
    return {"tablas": len(tables), "relaciones_activas_unidireccionales": len(actual_relations), "catalogo_origenes": "coincide con la referencia"}


def verify(data_dir: Path, project_dir: Path = ROOT / "powerbi") -> dict:
    origins, model_labels = reference_metadata()
    hashes = {}
    for name in FILES:
        data = (data_dir / name).read_bytes()
        require(data == reference_file(f"data/{name}"), f"{name} difiere del commit de referencia {REFERENCE[:7]}.")
        hashes[name] = hashlib.sha256(data).hexdigest()

    arrivals = read_csv(data_dir / FILES[0])
    require([r["date"] for r in arrivals] == monthly_dates(date(2009, 1, 1), 210), "Cobertura de llegadas incorrecta.")
    monthly = {}
    for row in arrivals:
        total = sum((number(row[key]) for key in origins), Decimal(0))
        require(close(total, number(row["reported_total"])), f"Total mensual incorrecto en {row['date']}.")
        monthly[row["date"]] = total

    occupancy = read_csv(data_dir / FILES[1])
    require([r["date"] for r in occupancy] == monthly_dates(date(2022, 1, 1), 36), "Cobertura de hospedaje incorrecta.")
    for row in occupancy:
        available, occupied = number(row["rooms_available"]), number(row["rooms_occupied"])
        require(available > 0 and occupied <= available, "Habitaciones inconsistentes.")

    predictions = read_csv(data_dir / FILES[2])
    metrics = read_csv(data_dir / FILES[3])
    require(len(metrics) == 3 and {r["model_id"] for r in metrics} == set(model_labels), "Claves de métricas incorrectas.")
    require(len(predictions) == 189, "Se esperan 189 predicciones.")
    seen = set()
    observations = {}
    for row in predictions:
        key = (row["date"], row["model_id"])
        require(key not in seen, "Predicción repetida para el mismo mes y modelo.")
        seen.add(key)
        require(row["model_label"] == model_labels.get(row["model_id"]), "Identidad del modelo incorrecta.")
        observed = number(row["observed"])
        number(row["estimate"])
        require(close(observed, monthly[row["date"]]), "El observado no coincide con las llegadas nacionales.")
        require(row["date"] not in observations or observations[row["date"]] == observed, "El observado cambia entre modelos.")
        observations[row["date"]] = observed

    recalculated = {}
    with localcontext() as context:
        context.prec = 40
        for metric in metrics:
            model_id = metric["model_id"]
            rows = sorted((r for r in predictions if r["model_id"] == model_id), key=lambda r: r["date"])
            require([r["date"] for r in rows] == monthly_dates(date(2021, 4, 1), 63), "Cobertura de evaluación incorrecta.")
            errors = [number(r["estimate"]) - number(r["observed"]) for r in rows]
            count = Decimal(len(rows))
            mae = sum((abs(e) for e in errors), Decimal(0)) / count
            rmse = (sum((e * e for e in errors), Decimal(0)) / count).sqrt()
            mape = sum((abs(e) / number(r["observed"]) * 100 for e, r in zip(errors, rows)), Decimal(0)) / count
            for field, value in (("mae", mae), ("rmse", rmse), ("mape", mape)):
                require(close(value, number(metric[field])), f"{field} no coincide para {model_id}.")
            recalculated[model_id] = {"meses": len(rows), "mae": str(mae), "rmse": str(rmse), "mape_porcentaje": str(mape)}

    december = observations["2025-12-01"]
    require(december == Decimal("365573.0218067979"), "Control de diciembre de 2025 incorrecto.")
    model = validate_definition(project_dir, origins)
    peak = max(monthly, key=monthly.get)
    return {
        "referencia_commit": REFERENCE,
        "alcance_validacion": "Fuentes CSV y estructura del proyecto; no ejecuta Power Query ni DAX, que se comprueban en Power BI Desktop.",
        "sha256": hashes,
        "filas_esperadas": {"Llegadas": len(arrivals) * len(origins), "Hospedaje": len(occupancy),
                            "Predicciones": len(predictions), "Metricas": len(metrics), "Observados": len(observations),
                            "Origenes": len(origins), "Modelos": len(model_labels),
                            "Calendario": (date(2026, 12, 31) - date(2009, 1, 1)).days + 1},
        "llegadas_total_sin_redondear": str(sum(monthly.values(), Decimal(0))),
        "mes_maximo": {"date": peak, "arrivals": str(monthly[peak])},
        "llegadas_2024": str(sum((v for k, v in monthly.items() if k.startswith("2024-")), Decimal(0))),
        "llegadas_2025": str(sum((v for k, v in monthly.items() if k.startswith("2025-")), Decimal(0))),
        "observado_diciembre_2025": str(december),
        "observado_evaluacion_sin_duplicar": str(sum(observations.values(), Decimal(0))),
        "metricas_recalculadas": recalculated,
        "definicion": model,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, help="Guarda el resultado como JSON.")
    args = parser.parse_args()
    try:
        result = verify(args.data_dir)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Verificación detenida: {exc}\n")
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
