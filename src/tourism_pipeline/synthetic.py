"""Datos sintéticos con la misma estructura que las fuentes reales.

Sirven para probar el pipeline sin datos institucionales. Los valores son
aleatorios y no representan ninguna cifra real.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


MOBILITY_FILE = "BD_moviidad_mensual.xlsx"
MIGRATION_FILE = "Base_Migracion_2009-2026jun.xlsx"
MIGRATION_SHEET = "Datos"

MOBILITY_STRUCTURE = {
    "Antigua": (
        ("Antigua Guatemala", "Antigua Guatemala"),
        ("Jocotenango", "Antigua Guatemala"),
        ("Volcan Acatenango Fuego", "Antigua Guatemala"),
    ),
    "Peten": (
        ("El Remate Y Alrededores Lago", "Peten"),
        ("Isla De Flores", "Peten"),
        ("Mundo Maya Aeropuerto", "Peten"),
    ),
    "Atitlan": (
        ("Panajachel", "Lago Atitlan"),
        ("San Pedro La Laguna", "Lago Atitlan"),
        ("Santiago Atitlan", "Lago Atitlan"),
    ),
    "Izabal": (
        ("Rio Dulce", "Izabal"),
        ("Livingston", "Izabal"),
    ),
    "Alta Verapaz": (
        ("Coban", "Coban"),
        ("Lanquin", "Coban"),
        ("Cuevas De Candelaria", "Coban"),
    ),
    "Playas Pacifico": (
        ("Monterrico", "Playas Del Pacifico"),
        ("El Paredon", "Playas Del Pacifico"),
        ("Las Lisas", "Playas Del Pacifico"),
        ("Puerto De San Jose", "Playas Del Pacifico"),
    ),
}

MOBILITY_MONTHS = tuple(
    pd.period_range("2025-09", "2025-12", freq="M").to_timestamp().tolist()
    + pd.period_range("2026-03", "2026-08", freq="M").to_timestamp().tolist()
)
MIGRATION_MONTHS = tuple(pd.period_range("2023-01", "2026-06", freq="M").to_timestamp())

COUNTRIES = ("Alemania", "Estados Unidos", "Mexico")
SEGMENTS = ("mayor a 1 dia", "menor a 1 dia")
MONTH_ABBREVIATIONS = (
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
)  # fmt: skip

PROBLEMS = (
    "missing_column",
    "duplicate_row",
    "zero_denominator",
    "negative_visitors",
    "invalid_date",
    "missing_values",
)


def build_mobility(seed: int = 7) -> dict[str, pd.DataFrame]:
    """Una tabla por hoja de la base mensual de movilidad."""
    rng = np.random.default_rng(seed)
    sheets: dict[str, pd.DataFrame] = {}
    for sheet, subdestinations in MOBILITY_STRUCTURE.items():
        rows = []
        for destination, group in subdestinations:
            for month in MOBILITY_MONTHS:
                for country in COUNTRIES:
                    for segment in SEGMENTS:
                        visitors = float(rng.integers(5, 500))
                        stay = 1.0 if segment == "menor a 1 dia" else float(rng.uniform(1.5, 5.0))
                        rows.append(
                            {
                                "destino": destination,
                                "sub_grupo": group,
                                "anio": float(month.year),
                                "mes": float(month.month),
                                "pais": country,
                                "es_consecutivo": segment,
                                "fecha": month,
                                "visitantes": visitors,
                                "dias_persona": visitors * stay,
                                "permanencia_prom": stay,
                            }
                        )
        sheets[sheet] = pd.DataFrame(rows)
    return sheets


def build_migration(seed: int = 7) -> pd.DataFrame:
    """Tabla en formato largo con la misma estructura de la base de migración."""
    rng = np.random.default_rng(seed + 1)
    rows = []
    for month in MIGRATION_MONTHS:
        for traveler in ("Turista", "Excursionista", "Viajero"):
            for route, border in (("Aérea", "01 La Aurora"), ("Terrestre", "05 Tecún Umán")):
                for country in ("Estados Unidos", "Mexico"):
                    rows.append(
                        {
                            "Año": month.year,
                            "Mes cod": month.month,
                            "Mes": MONTH_ABBREVIATIONS[month.month - 1],
                            "Vía": route,
                            "Frontera": border,
                            "País": country,
                            "Región": "AMERICA",
                            "Región dos": "América del Norte",
                            "Regiones OMT": "AMERICA DEL NORTE",
                            "MCEO": "01 NORTEAMERICA",
                            "Agrupación Residencia": country,
                            "Tipo de Viajero": traveler,
                            "Viajero": float(rng.integers(1_000, 50_000)),
                        }
                    )
    return pd.DataFrame(rows)


def apply_problem(
    mobility: dict[str, pd.DataFrame],
    migration: pd.DataFrame,
    problem: str,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Introduce un problema conocido en copias de las tablas sintéticas."""
    if problem not in PROBLEMS:
        raise ValueError(f"Problema desconocido: {problem}. Opciones: {', '.join(PROBLEMS)}.")
    mobility = {sheet: frame.copy() for sheet, frame in mobility.items()}
    migration = migration.copy()
    first = next(iter(mobility))

    if problem == "missing_column":
        mobility = {sheet: frame.drop(columns="visitantes") for sheet, frame in mobility.items()}
    elif problem == "duplicate_row":
        frame = mobility[first]
        mobility[first] = pd.concat([frame, frame.iloc[:2]], ignore_index=True)
    elif problem == "zero_denominator":
        december = (migration["Año"] == 2025) & (migration["Mes cod"] == 12)
        migration.loc[december, "Viajero"] = 0.0
    elif problem == "negative_visitors":
        mobility[first].loc[0, "visitantes"] = -10.0
    elif problem == "invalid_date":
        mobility[first]["fecha"] = mobility[first]["fecha"].astype(object)
        mobility[first].loc[0, "fecha"] = "no-es-una-fecha"
    elif problem == "missing_values":
        mobility[first].loc[:4, "visitantes"] = np.nan
    return mobility, migration


def write_synthetic_sources(
    directory: str | Path,
    problem: str | None = None,
    seed: int = 7,
) -> dict[str, Path]:
    """Escribe las dos fuentes sintéticas como archivos de Excel en `directory`."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    mobility = build_mobility(seed)
    migration = build_migration(seed)
    if problem is not None:
        mobility, migration = apply_problem(mobility, migration, problem)

    mobility_path = directory / MOBILITY_FILE
    with pd.ExcelWriter(mobility_path, engine="openpyxl") as writer:
        for sheet, frame in mobility.items():
            frame.to_excel(writer, sheet_name=sheet, index=False)
    migration_path = directory / MIGRATION_FILE
    with pd.ExcelWriter(migration_path, engine="openpyxl") as writer:
        migration.to_excel(writer, sheet_name=MIGRATION_SHEET, index=False)
    return {"mobility": mobility_path, "migration": migration_path}
