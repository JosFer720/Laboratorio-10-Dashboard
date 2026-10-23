from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


EMPTY_MODEL_STATUS = "No hay un modelo válido seleccionado."


def _common_model_ids(
    predictions: pd.DataFrame, metrics: pd.DataFrame
) -> list[str]:
    if "model_id" not in predictions or "model_id" not in metrics:
        return []
    predicted = set(predictions["model_id"].dropna())
    return [
        model_id
        for model_id in metrics["model_id"].dropna().drop_duplicates()
        if model_id in predicted
    ]


def model_options(
    predictions: pd.DataFrame, metrics: pd.DataFrame
) -> list[dict[str, str]]:
    valid_ids = set(_common_model_ids(predictions, metrics))
    rows = metrics.loc[metrics.get("model_id", pd.Series(dtype=str)).isin(valid_ids)]
    return [
        {"label": str(row.model_label), "value": str(row.model_id)}
        for row in rows.itertuples()
    ]


def initial_model_selection(
    predictions: pd.DataFrame, metrics: pd.DataFrame
) -> dict[str, str | None]:
    model_ids = _common_model_ids(predictions, metrics)
    return {"model": model_ids[0] if model_ids else None}


def sanitize_model_selection(
    value: object, predictions: pd.DataFrame, metrics: pd.DataFrame
) -> dict[str, str | None]:
    valid_ids = set(_common_model_ids(predictions, metrics))
    model_id = value if isinstance(value, str) and value in valid_ids else None
    return {"model": model_id}


def selected_model_rows(
    predictions: pd.DataFrame,
    metrics: pd.DataFrame,
    selection: Mapping[str, object] | None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    model_id = selection.get("model") if isinstance(selection, Mapping) else None
    valid = sanitize_model_selection(model_id, predictions, metrics)["model"]
    if valid is None:
        return predictions.iloc[:0].copy(), metrics.iloc[:0].copy()
    return (
        predictions.loc[predictions["model_id"] == valid].copy(),
        metrics.loc[metrics["model_id"] == valid].copy(),
    )


def _spanish_number(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def metric_values(metrics: pd.DataFrame) -> tuple[str, str, str]:
    if metrics.empty:
        return "—", "—", "—"
    row = metrics.iloc[0]
    return (
        _spanish_number(float(row["mae"])),
        _spanish_number(float(row["rmse"])),
        f"{_spanish_number(float(row['mape']), 1)} %",
    )


def model_status(metrics: pd.DataFrame) -> str:
    if metrics.empty:
        return EMPTY_MODEL_STATUS
    label = str(metrics.iloc[0]["model_label"])
    return (
        f"{label} · evaluación histórica de abril de 2021 a junio de 2026."
    )
