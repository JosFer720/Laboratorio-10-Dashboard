from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from tourism_dashboard.data import MONTH_NAMES

FREQUENCIES = {"month": "M", "quarter": "Q", "year": "Y"}
DETAIL_OPTIONS = [
    {"label": "Año", "value": "year"},
    {"label": "Trimestre", "value": "quarter"},
    {"label": "Mes", "value": "month"},
]


def display_origin(origin: str) -> str:
    return {"Canada": "Canadá", "Mexico": "México"}.get(
        origin, origin.replace("America", "América")
    )


def month_label(value: str | pd.Timestamp) -> str:
    date = pd.Timestamp(value)
    return f"{MONTH_NAMES[date.month]} de {date.year}"


def month_options(arrivals: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {"label": month_label(date), "value": date.strftime("%Y-%m-%d")}
        for date in sorted(arrivals["date"].unique())
    ]


def market_options(arrivals: pd.DataFrame) -> list[dict[str, str]]:
    options = [{"label": "Todos los mercados", "value": "all"}]
    for region, rows in arrivals.groupby("origin_region", sort=False):
        origins = rows[["origin", "origin_level"]].drop_duplicates()
        if len(origins) > 1:
            options.append(
                {
                    "label": f"{display_origin(region)} · región completa",
                    "value": f"region:{region}",
                }
            )
        for origin, level in origins.itertuples(index=False, name=None):
            label = {"country": "país", "region": "agregado", "segment": "segmento"}[
                level
            ]
            options.append(
                {
                    "label": f"{display_origin(origin)} · {label}",
                    "value": f"origin:{origin}",
                }
            )
    return options


def filter_market(arrivals: pd.DataFrame, market: str | None) -> pd.DataFrame:
    if market == "all":
        return arrivals
    if not isinstance(market, str) or ":" not in market:
        return arrivals.iloc[:0]
    kind, value = market.split(":", 1)
    column = {"region": "origin_region", "origin": "origin"}.get(kind)
    if column is None:
        return arrivals.iloc[:0]
    return arrivals.loc[arrivals[column] == value]


def filter_arrivals(
    arrivals: pd.DataFrame,
    start_date: str | None,
    end_date: str | None,
    market: str | None,
) -> pd.DataFrame:
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if pd.isna(start) or pd.isna(end) or start > end:
        return arrivals.iloc[:0]
    rows = filter_market(arrivals, market)
    return rows.loc[rows["date"].between(start, end)]


def aggregate_arrivals(arrivals: pd.DataFrame, detail: str) -> pd.DataFrame:
    frequency = FREQUENCIES[detail]
    periods = arrivals["date"].dt.to_period(frequency)
    totals = arrivals.groupby(periods, sort=True)["arrivals"].sum()
    result = totals.rename_axis("period").reset_index()
    result["period_key"] = result["period"].astype(str)
    result["date"] = result["period"].dt.start_time
    result["months"] = arrivals.groupby(periods)["date"].nunique().to_numpy()
    result["label"] = [period_label(period, detail) for period in result["period"]]
    return result


def period_label(period: pd.Period, detail: str) -> str:
    if detail == "month":
        return month_label(period.start_time)
    if detail == "quarter":
        return f"Trimestre {period.quarter} de {period.year}"
    return str(period.year)


def make_selection(
    filtered: pd.DataFrame,
    market: str | None,
    detail: str,
    event: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    dates = filtered["date"].drop_duplicates().sort_values()
    selected_keys: set[str] = set()
    if isinstance(event, Mapping) and isinstance(event.get("points"), list):
        for point in event["points"]:
            if not isinstance(point, Mapping):
                continue
            custom = point.get("customdata")
            if (
                isinstance(custom, (list, tuple))
                and custom
                and isinstance(custom[0], str)
            ):
                selected_keys.add(custom[0])
    matched = dates.dt.to_period(FREQUENCIES[detail]).astype(str).isin(selected_keys)
    is_selected = bool(matched.any())
    if is_selected:
        dates = dates.loc[matched]
    return {
        "dates": dates.dt.strftime("%Y-%m-%d").tolist(),
        "market": market,
        "granularity": detail,
        "is_selected": is_selected,
    }


def apply_selection(
    arrivals: pd.DataFrame, selection: Mapping[str, Any] | None
) -> pd.DataFrame:
    """Recupera las filas observadas del contrato de v1-selection."""
    if not isinstance(selection, Mapping) or not isinstance(
        selection.get("dates"), list
    ):
        return arrivals.iloc[:0]
    dates = pd.to_datetime(
        [date for date in selection["dates"] if isinstance(date, str)],
        format="%Y-%m-%d",
        errors="coerce",
    )
    rows = filter_market(arrivals, selection.get("market"))
    return rows.loc[rows["date"].isin(dates)]


def selection_label(selection: Mapping[str, Any]) -> str:
    dates = selection["dates"]
    if not dates:
        return "No hay meses disponibles. Revisa el periodo y el mercado."
    if not selection["is_selected"]:
        return f"Periodo completo del filtro · {len(dates)} meses con información"
    names = [month_label(date) for date in dates[:3]]
    suffix = f" y {len(dates) - 3} más" if len(dates) > 3 else ""
    return "Selección: " + "; ".join(names) + suffix
