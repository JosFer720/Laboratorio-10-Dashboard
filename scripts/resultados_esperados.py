"""Calcula los resultados esperados que sirven para verificar el informe de Power BI.

Usa los mismos CSV y las mismas reglas de agregación del tablero en Dash:
las llegadas de un período son la suma de los orígenes de cada mes, una región
suma sus orígenes y las métricas de los modelos se recalculan sobre los 63
meses de evaluación.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tourism_dashboard.data import (  # noqa: E402
    MONTH_NAMES,
    load_arrivals,
    load_model_metrics,
    load_model_predictions,
    load_occupancy,
)


DATA = ROOT / "data"


def _number(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def _month(date: pd.Timestamp, capitalized: bool = True) -> str:
    name = MONTH_NAMES[date.month]
    return f"{name if capitalized else name.lower()} de {date.year}"


def build_report() -> str:
    arrivals = load_arrivals(DATA / "arrivals_migration_2009_2026.csv")
    occupancy = load_occupancy(DATA / "hotel_occupancy_inguat_2022_2024.csv")
    predictions = load_model_predictions(DATA / "model_predictions_s0.csv")
    metrics = load_model_metrics(DATA / "model_metrics_s0.csv")

    monthly = arrivals.groupby("date")["arrivals"].sum()
    lines = [
        "# Resultados esperados",
        "",
        "Valores calculados con `python scripts/resultados_esperados.py` a partir de los CSV de `data/`, "
        "con las mismas reglas de agregación del tablero en Dash. Sirven para comprobar que el informe "
        "de Power BI muestra lo mismo. Las cifras de llegadas conservan decimales en la fuente; aquí se "
        "redondean a enteros solo para leerlas.",
        "",
        "## Indicadores generales",
        "",
        "| Indicador | Filtros | Valor esperado |",
        "|---|---|---|",
        f"| Llegadas del período completo | Enero de 2009 a junio de 2026, todos los mercados | {_number(monthly.sum())} |",
        f"| Mes con más llegadas | Período completo, todos los mercados | {_month(monthly.idxmax())}: {_number(monthly.max())} |",
        f"| Meses con información | Período completo, todos los mercados | {monthly.size} |",
    ]
    for year in (2024, 2025):
        total = monthly[monthly.index.year == year].sum()
        lines.append(f"| Llegadas de {year} | Enero a diciembre de {year}, todos los mercados | {_number(total)} |")
    rate = occupancy["rooms_occupied"].sum() / occupancy["rooms_available"].sum() * 100
    lines.append(
        f"| Ocupación hotelera de 2022 a 2024 | Habitaciones ocupadas entre disponibles | {_number(rate, 1)} % |"
    )

    lines += ["", "## Prueba 1: mes con más llegadas en 2025", ""]
    year = monthly[monthly.index.year == 2025]
    lines += [
        f"Con el período de enero a diciembre de 2025 y todos los mercados, el mes con más llegadas es "
        f"{_month(year.idxmax(), False)}, con {_number(year.max())} llegadas, y el de menos es "
        f"{_month(year.idxmin(), False)}, con {_number(year.min())}. El total del año es {_number(year.sum())}.",
        "",
        "| Mes | Llegadas |",
        "|---|---|",
        *[f"| {_month(date)} | {_number(value)} |" for date, value in year.items()],
    ]

    lines += ["", "## Prueba 2: de las regiones a los países de América Central en 2025", ""]
    rows = arrivals.loc[arrivals["year"] == 2025]
    regions = rows.groupby("origin_region")["arrivals"].sum().sort_values(ascending=False)
    central = (
        rows.loc[rows["origin_region"] == "América Central"]
        .groupby("origin")["arrivals"]
        .sum()
        .sort_values(ascending=False)
    )
    lines += [
        "Llegadas de 2025 por región:",
        "",
        "| Región | Llegadas | Participación |",
        "|---|---|---|",
        *[
            f"| {region} | {_number(value)} | {_number(value / regions.sum() * 100, 1)} % |"
            for region, value in regions.items()
        ],
        "",
        f"Al bajar a los países de América Central, el que más aporta es {central.index[0]}, con "
        f"{_number(central.iloc[0])} llegadas, el {_number(central.iloc[0] / central.sum() * 100, 1)} % de la región:",
        "",
        "| Origen | Llegadas | Participación en la región |",
        "|---|---|---|",
        *[
            f"| {origin} | {_number(value)} | {_number(value / central.sum() * 100, 1)} % |"
            for origin, value in central.items()
        ],
        "",
        "La categoría Guatemala vale cero desde enero de 2023 en la fuente, por eso aparece con cero.",
    ]

    lines += ["", "## Prueba 3: desempeño de los tres modelos", ""]
    lines += [
        "Los tres modelos estiman la misma serie mensual de turistas y excursionistas en los mismos 63 "
        "meses de evaluación, de abril de 2021 a junio de 2026, con entrenamiento hasta marzo de 2021. "
        "Sus métricas son comparables entre sí.",
        "",
        "| Modelo | MAE | RMSE | MAPE | Error en diciembre de 2025 (estimado − observado) |",
        "|---|---|---|---|---|",
    ]
    december = predictions.loc[predictions["date"] == pd.Timestamp("2025-12-01")].set_index("model_id")
    for row in metrics.itertuples():
        rows = predictions.loc[predictions["model_id"] == row.model_id]
        error = rows["estimate"] - rows["observed"]
        recalculated = (
            error.abs().mean(),
            np.sqrt((error**2).mean()),
            (error.abs() / rows["observed"]).mean() * 100,
        )
        assert np.allclose(recalculated, (row.mae, row.rmse, row.mape))
        point = december.loc[row.model_id]
        lines.append(
            f"| {row.model_label} | {_number(row.mae)} | {_number(row.rmse)} | {_number(row.mape, 1)} % "
            f"| {_number(point['estimate'] - point['observed'])} |"
        )
    best = metrics.loc[metrics["mape"].idxmin()]
    observed = december.iloc[0]["observed"]
    lines += [
        "",
        f"El modelo con menor MAPE es {best['model_label']}. El valor observado de diciembre de 2025 "
        f"es {_number(observed)} y debe ser el mismo con cualquier modelo seleccionado: si cambia, el "
        "observado se está sumando entre modelos.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "docs" / "lab12" / "resultados_esperados.md",
        help="Archivo Markdown donde se escriben los resultados.",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
