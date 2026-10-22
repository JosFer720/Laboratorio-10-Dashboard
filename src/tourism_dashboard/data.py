from __future__ import annotations

from pathlib import Path

import pandas as pd


ORIGIN_METADATA = {
    "canada": ("Canada", "America del Norte", "country"),
    "united_states": ("Estados Unidos", "America del Norte", "country"),
    "mexico": ("Mexico", "America del Norte", "country"),
    "belize": ("Belice", "America Central", "country"),
    "el_salvador": ("El Salvador", "America Central", "country"),
    "honduras": ("Honduras", "America Central", "country"),
    "rest_of_central_america": (
        "Resto de America Central",
        "America Central",
        "region",
    ),
    "south_america": ("America del Sur", "America del Sur", "region"),
    "europe": ("Europa", "Europa", "region"),
    "rest_of_world": ("Resto del mundo", "Resto del mundo", "region"),
    "cruise_passengers": ("Cruceristas", "Cruceristas", "segment"),
}

MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}

CANONICAL_COLUMNS = (
    "date",
    "year",
    "quarter",
    "month",
    "month_name",
    "destination_zone",
    "origin",
    "origin_region",
    "origin_level",
    "arrivals",
)


class TourismDataError(ValueError):
    """Indica que la fuente turistica no cumple el contrato esperado."""


def load_arrivals(path: str | Path) -> pd.DataFrame:
    source_path = Path(path)
    if not source_path.is_file():
        raise TourismDataError(f"No se encontro el archivo de datos: {source_path}")
    if source_path.suffix.lower() != ".csv":
        raise TourismDataError("El archivo de llegadas debe estar en formato CSV.")

    try:
        raw = pd.read_csv(source_path, encoding="utf-8-sig")
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise TourismDataError("No fue posible leer el archivo de llegadas.") from exc

    required = {"date", "reported_total", *ORIGIN_METADATA}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise TourismDataError(
            "Faltan columnas requeridas: " + ", ".join(missing)
        )

    data = raw.loc[:, ["date", *ORIGIN_METADATA, "reported_total"]].copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any() or not data["date"].dt.is_month_start.all():
        raise TourismDataError("La columna date contiene meses invalidos.")
    if data["date"].duplicated().any():
        raise TourismDataError("La columna date contiene meses duplicados.")

    for column in ORIGIN_METADATA:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data["reported_total"] = pd.to_numeric(
        data["reported_total"], errors="coerce"
    )
    values = data.loc[:, list(ORIGIN_METADATA)]
    if values.isna().any().any() or data["reported_total"].isna().any():
        raise TourismDataError("Las llegadas contienen valores no numericos o vacios.")
    if (values < 0).any().any() or (data["reported_total"] < 0).any():
        raise TourismDataError("Las llegadas contienen valores negativos.")
    if ((values % 1) != 0).any().any() or (
        (data["reported_total"] % 1) != 0
    ).any():
        raise TourismDataError("Las llegadas deben ser numeros enteros.")
    total_difference = values.sum(axis=1) - data["reported_total"]
    if total_difference.abs().gt(1).any():
        raise TourismDataError(
            "Las categorias no coinciden con el total mensual reportado."
        )

    tidy = data.melt(
        id_vars="date",
        value_vars=list(ORIGIN_METADATA),
        var_name="origin_key",
        value_name="arrivals",
    )
    tidy["year"] = tidy["date"].dt.year.astype("Int64")
    tidy["quarter"] = tidy["date"].dt.quarter.astype("Int64")
    tidy["month"] = tidy["date"].dt.month.astype("Int64")
    tidy["month_name"] = tidy["month"].map(MONTH_NAMES)
    tidy["destination_zone"] = "Guatemala"
    tidy["origin"] = tidy["origin_key"].map(
        {key: metadata[0] for key, metadata in ORIGIN_METADATA.items()}
    )
    tidy["origin_region"] = tidy["origin_key"].map(
        {key: metadata[1] for key, metadata in ORIGIN_METADATA.items()}
    )
    tidy["origin_level"] = tidy["origin_key"].map(
        {key: metadata[2] for key, metadata in ORIGIN_METADATA.items()}
    )
    tidy["arrivals"] = tidy["arrivals"].astype("Int64")
    tidy["origin_order"] = tidy["origin_key"].map(
        {key: index for index, key in enumerate(ORIGIN_METADATA)}
    )
    tidy = tidy.sort_values(["date", "origin_order"], kind="stable")

    return tidy.loc[:, CANONICAL_COLUMNS].reset_index(drop=True)
