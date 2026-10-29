from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


DESTINATION_COLUMNS = ["sheet", "destination_group", "destination"]
FACTOR_COLUMNS = (
    "sheet",
    "destination_group",
    "destination",
    "target_period",
    "factor",
    "months_used",
    "first_month",
    "last_month",
)


class RepartoError(ValueError):
    """No se puede calcular el factor de reparto con los meses disponibles."""


def monthly_ratios(
    visitors: pd.DataFrame, entries: pd.DataFrame, months: Iterable[pd.Timestamp]
) -> pd.DataFrame:
    """Cociente entre los visitantes del subdestino y las entradas nacionales del mismo mes."""
    months = list(months)
    rows = visitors.loc[visitors["period"].isin(months)].merge(
        entries, on="period", how="inner", validate="many_to_one"
    )
    if (rows["entries"] <= 0).any():
        bad = rows.loc[rows["entries"] <= 0, "period"].dt.strftime("%Y-%m").unique()
        raise RepartoError(
            "Las entradas nacionales deben ser positivas para calcular el factor: "
            + ", ".join(bad)
        )
    return rows.assign(ratio=rows["visitors"] / rows["entries"])


def reparto_factors(
    visitors: pd.DataFrame,
    entries: pd.DataFrame,
    fit_months: Iterable[pd.Timestamp],
    target: pd.Timestamp,
) -> pd.DataFrame:
    """Factor de reparto de cada subdestino para estimar el mes `target`.

    Solo se usan meses de ajuste anteriores a `target`. Se promedian los
    cocientes mensuales; nunca se suman visitantes de varios meses.
    """
    target = pd.Timestamp(target)
    months = [month for month in fit_months if month < target]
    if not months:
        raise RepartoError(
            f"No hay meses de ajuste anteriores a {target:%Y-%m} para calcular el factor."
        )
    ratios = monthly_ratios(visitors, entries, months)
    if ratios.empty:
        raise RepartoError(
            f"Ningún mes de ajuste anterior a {target:%Y-%m} tiene movilidad y entradas a la vez."
        )
    factors = (
        ratios.groupby(DESTINATION_COLUMNS, sort=True)
        .agg(
            factor=("ratio", "mean"),
            months_used=("period", "nunique"),
            first_month=("period", "min"),
            last_month=("period", "max"),
        )
        .reset_index()
    )
    factors["target_period"] = target
    return factors.loc[:, FACTOR_COLUMNS]
