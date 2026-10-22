from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd


ORIGIN_METADATA = {
    "canada": ("Canadá", "América del Norte", "country"),
    "united_states": ("Estados Unidos", "América del Norte", "country"),
    "mexico": ("México", "América del Norte", "country"),
    "belize": ("Belice", "América Central", "country"),
    "el_salvador": ("El Salvador", "América Central", "country"),
    "honduras": ("Honduras", "América Central", "country"),
    "rest_of_central_america": (
        "Resto de América Central",
        "América Central",
        "region",
    ),
    "south_america": ("América del Sur", "América del Sur", "region"),
    "europe": ("Europa", "Europa", "region"),
    "rest_of_world": ("Resto del mundo", "Resto del mundo", "region"),
    "guatemala": ("Guatemala", "América Central", "country"),
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


OCCUPANCY_COLUMNS = (
    "date",
    "year",
    "quarter",
    "month",
    "month_name",
    "rooms_available",
    "rooms_occupied",
    "occupancy_rate",
    "reported_occupancy_pct",
)

MODEL_PREDICTION_COLUMNS = (
    "date",
    "model_id",
    "model_label",
    "observed",
    "estimate",
)

MODEL_METRIC_COLUMNS = (
    "model_id",
    "model_label",
    "source_lab",
    "source_commit",
    "mae",
    "rmse",
    "mape",
    "aic",
    "bic",
    "train_end",
    "evaluation_start",
    "evaluation_end",
)

MODEL_LABELS = {
    "lstm-catch22-contexto-w24": "LSTM catch22 (ventana 24)",
    "prophet": "Prophet",
    "arima-1-1-1": "ARIMA(1,1,1)",
}
MODEL_SOURCES = {
    "lstm-catch22-contexto-w24": (
        "Laboratorio 2",
        "f2155dcc34bc9abae93797fb5ec3ceb962833f38",
    ),
    "prophet": (
        "Laboratorio 1",
        "534cfd5fc7586122632dab4c28aaddb6587c281d",
    ),
    "arima-1-1-1": (
        "Laboratorio 1",
        "534cfd5fc7586122632dab4c28aaddb6587c281d",
    ),
}
MODEL_EVALUATION_START = pd.Timestamp("2021-04-01")
MODEL_EVALUATION_END = pd.Timestamp("2026-06-01")
MODEL_TRAIN_END = pd.Timestamp("2021-03-01")
MODEL_EVALUATION_MONTHS = pd.date_range(
    MODEL_EVALUATION_START, MODEL_EVALUATION_END, freq="MS"
)


class TourismDataError(ValueError):
    """Indica que la fuente turistica no cumple el contrato esperado."""


def _read_csv(path: str | Path, label: str) -> pd.DataFrame:
    source_path = Path(path)
    if not source_path.is_file():
        raise TourismDataError(f"No se encontro el archivo de datos: {source_path}")
    if source_path.suffix.lower() != ".csv":
        raise TourismDataError(f"El archivo de {label} debe estar en formato CSV.")

    try:
        return pd.read_csv(source_path, encoding="utf-8-sig")
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise TourismDataError(f"No fue posible leer el archivo de {label}.") from exc


def _parse_months(dates: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(dates, errors="coerce")
    if parsed.isna().any() or not parsed.dt.is_month_start.all():
        raise TourismDataError("La columna date contiene meses invalidos.")
    if parsed.duplicated().any():
        raise TourismDataError("La columna date contiene meses duplicados.")
    return parsed


def _add_calendar_fields(data: pd.DataFrame) -> pd.DataFrame:
    data["year"] = data["date"].dt.year.astype("Int64")
    data["quarter"] = data["date"].dt.quarter.astype("Int64")
    data["month"] = data["date"].dt.month.astype("Int64")
    data["month_name"] = data["month"].map(MONTH_NAMES)
    return data


def load_arrivals(path: str | Path) -> pd.DataFrame:
    raw = _read_csv(path, "llegadas")

    required = {"date", "reported_total", *ORIGIN_METADATA}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise TourismDataError(
            "Faltan columnas requeridas: " + ", ".join(missing)
        )

    data = raw.loc[:, ["date", *ORIGIN_METADATA, "reported_total"]].copy()
    data["date"] = _parse_months(data["date"])

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
    total_difference = values.sum(axis=1) - data["reported_total"]
    if total_difference.abs().gt(1e-6).any():
        raise TourismDataError(
            "Las categorias no coinciden con el total mensual reportado."
        )

    tidy = data.melt(
        id_vars="date",
        value_vars=list(ORIGIN_METADATA),
        var_name="origin_key",
        value_name="arrivals",
    )
    tidy = _add_calendar_fields(tidy)
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
    tidy["arrivals"] = tidy["arrivals"].astype("Float64")
    tidy["origin_order"] = tidy["origin_key"].map(
        {key: index for index, key in enumerate(ORIGIN_METADATA)}
    )
    tidy = tidy.sort_values(["date", "origin_order"], kind="stable")

    return tidy.loc[:, CANONICAL_COLUMNS].reset_index(drop=True)


def load_occupancy(path: str | Path) -> pd.DataFrame:
    raw = _read_csv(path, "ocupacion hotelera")

    counts = ["rooms_available", "rooms_occupied", "reported_occupancy_pct"]
    missing = sorted({"date", *counts}.difference(raw.columns))
    if missing:
        raise TourismDataError(
            "Faltan columnas requeridas: " + ", ".join(missing)
        )

    data = raw.loc[:, ["date", *counts]].copy()
    data["date"] = _parse_months(data["date"])

    for column in counts:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    values = data.loc[:, counts]
    if values.isna().any().any():
        raise TourismDataError("La ocupacion contiene valores no numericos o vacios.")
    if (values < 0).any().any() or ((values % 1) != 0).any().any():
        raise TourismDataError("La ocupacion debe tener numeros enteros no negativos.")
    if (data["rooms_available"] == 0).any():
        raise TourismDataError("Hay meses sin habitaciones disponibles.")
    if (data["rooms_occupied"] > data["rooms_available"]).any():
        raise TourismDataError(
            "Las habitaciones ocupadas superan a las disponibles."
        )

    for column in counts:
        data[column] = data[column].astype("Int64")
    data["occupancy_rate"] = (
        data["rooms_occupied"] / data["rooms_available"] * 100
    ).astype("Float64")
    data = _add_calendar_fields(data).sort_values("date", kind="stable")

    return data.loc[:, OCCUPANCY_COLUMNS].reset_index(drop=True)


def _require_columns(raw: pd.DataFrame, columns: tuple[str, ...]) -> None:
    missing = sorted(set(columns).difference(raw.columns))
    if missing:
        raise TourismDataError(
            "Faltan columnas requeridas: " + ", ".join(missing)
        )


def _parse_model_months(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.isna().any() or not parsed.dt.is_month_start.all():
        raise TourismDataError("Las fechas de modelos deben ser meses validos.")
    return parsed


def _validate_model_identity(data: pd.DataFrame) -> None:
    if set(data["model_id"]) != set(MODEL_LABELS):
        raise TourismDataError("Los IDs de modelos no coinciden con el contrato.")
    expected_labels = data["model_id"].map(MODEL_LABELS)
    if not data["model_label"].eq(expected_labels).all():
        raise TourismDataError("Las etiquetas de modelos no coinciden con sus IDs.")


def load_model_predictions(path: str | Path) -> pd.DataFrame:
    raw = _read_csv(path, "predicciones de modelos")
    _require_columns(raw, MODEL_PREDICTION_COLUMNS)
    data = raw.loc[:, MODEL_PREDICTION_COLUMNS].copy()
    data["date"] = _parse_model_months(data["date"])
    _validate_model_identity(data)

    if data.duplicated(["model_id", "date"]).any():
        raise TourismDataError("Las predicciones contienen meses duplicados.")

    numeric = ["observed", "estimate"]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    values = data.loc[:, numeric]
    if values.isna().any().any() or not np.isfinite(values.to_numpy()).all():
        raise TourismDataError("Las predicciones deben contener valores finitos.")
    if (values < 0).any().any():
        raise TourismDataError("Las predicciones contienen valores negativos.")

    for model_id, rows in data.groupby("model_id"):
        dates = rows["date"].sort_values().reset_index(drop=True)
        if len(rows) != len(MODEL_EVALUATION_MONTHS):
            raise TourismDataError(
                f"El modelo {model_id} debe contener exactamente 63 filas."
            )
        if not dates.equals(pd.Series(MODEL_EVALUATION_MONTHS)):
            raise TourismDataError(
                "Cada modelo debe cubrir todo el rango mensual de evaluacion."
            )

    if not data.groupby("date")["observed"].nunique(dropna=False).eq(1).all():
        raise TourismDataError(
            "Los valores observados deben ser identicos entre modelos."
        )

    order = {model_id: index for index, model_id in enumerate(MODEL_LABELS)}
    data["_model_order"] = data["model_id"].map(order)
    data = data.sort_values(["_model_order", "date"], kind="stable")
    return data.loc[:, MODEL_PREDICTION_COLUMNS].reset_index(drop=True)


def load_model_metrics(path: str | Path) -> pd.DataFrame:
    raw = _read_csv(path, "metricas de modelos")
    _require_columns(raw, MODEL_METRIC_COLUMNS)
    data = raw.loc[:, MODEL_METRIC_COLUMNS].copy()
    _validate_model_identity(data)

    if data["model_id"].duplicated().any() or len(data) != len(MODEL_LABELS):
        raise TourismDataError("Debe existir una fila de metricas por modelo.")
    if not data["source_commit"].astype(str).str.fullmatch(
        re.compile(r"[0-9a-f]{40}")
    ).all():
        raise TourismDataError("Cada commit fuente debe usar el hash completo.")
    if data["source_lab"].isna().any() or data["source_lab"].eq("").any():
        raise TourismDataError("Cada modelo debe declarar su laboratorio fuente.")
    expected_sources = data["model_id"].map(MODEL_SOURCES)
    actual_sources = list(zip(data["source_lab"], data["source_commit"]))
    if actual_sources != expected_sources.tolist():
        raise TourismDataError("La procedencia de los modelos no coincide.")

    required_metrics = ["mae", "rmse", "mape"]
    optional_metrics = ["aic", "bic"]
    for column in required_metrics:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    for column in optional_metrics:
        supplied = raw[column].notna() & raw[column].astype(str).str.strip().ne("")
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data.loc[supplied, column].isna().any():
            raise TourismDataError("Las metricas opcionales deben ser numericas.")
    required_values = data.loc[:, required_metrics]
    supplied_values = data.loc[:, [*required_metrics, *optional_metrics]]
    if required_values.isna().any().any() or not np.isfinite(
        supplied_values.to_numpy(dtype=float, na_value=np.nan)[
            ~np.isnan(supplied_values.to_numpy(dtype=float, na_value=np.nan))
        ]
    ).all():
        raise TourismDataError("Las metricas requeridas deben ser finitas.")
    if (supplied_values < 0).any().any():
        raise TourismDataError("Las metricas no pueden ser negativas.")

    expected_dates = {
        "train_end": MODEL_TRAIN_END,
        "evaluation_start": MODEL_EVALUATION_START,
        "evaluation_end": MODEL_EVALUATION_END,
    }
    for column, expected in expected_dates.items():
        data[column] = _parse_model_months(data[column])
        if not data[column].eq(expected).all():
            raise TourismDataError("El rango de evaluacion no coincide con el contrato.")

    order = {model_id: index for index, model_id in enumerate(MODEL_LABELS)}
    data["_model_order"] = data["model_id"].map(order)
    data = data.sort_values("_model_order", kind="stable")
    return data.loc[:, MODEL_METRIC_COLUMNS].reset_index(drop=True)
