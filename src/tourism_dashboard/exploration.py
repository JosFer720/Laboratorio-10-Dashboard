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


def aggregate_markets(rows: pd.DataFrame) -> pd.DataFrame:
    """Suma las llegadas de cada origen y calcula su participación."""
    columns = ["origin", "origin_level", "arrivals", "share"]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    totals = (
        rows.groupby(["origin", "origin_level"], sort=False)["arrivals"]
        .sum()
        .reset_index()
    )
    totals["arrivals"] = totals["arrivals"].astype("Float64")
    total = totals["arrivals"].sum()
    totals["share"] = totals["arrivals"] / total * 100 if total else 0.0
    return totals.sort_values("arrivals", ascending=False, kind="stable").reset_index(
        drop=True
    )


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


def market_labels(arrivals: pd.DataFrame) -> dict[str, str]:
    return {option["value"]: option["label"] for option in market_options(arrivals)}


def markets_caption(selection: Mapping[str, Any], labels: Mapping[str, str]) -> str:
    market = labels.get(selection.get("market"), "sin mercado válido")
    return f"Mercado: {market} · {selection_label(selection)}"


SUBPERIOD_LABELS = {
    "month": [name[:3] for name in MONTH_NAMES.values()],
    "quarter": ["T1", "T2", "T3", "T4"],
    "year": ["Año completo"],
}
SEASONALITY_MODES = [
    {"label": "Llegadas", "value": "arrivals"},
    {"label": "% del año", "value": "share"},
]


def _subperiod(dates: pd.Series, detail: str) -> pd.Series:
    if detail == "month":
        return dates.dt.month
    if detail == "quarter":
        return dates.dt.quarter
    return pd.Series(1, index=dates.index)


def seasonal_cells(filtered: pd.DataFrame, detail: str) -> pd.DataFrame:
    """Suma las llegadas de cada año y subperiodo, y su peso dentro del año."""
    columns = [
        "year",
        "subperiod",
        "period_key",
        "label",
        "arrivals",
        "share",
        "months",
    ]
    if filtered.empty:
        return pd.DataFrame(columns=columns)
    cells = aggregate_arrivals(filtered, detail)
    cells["year"] = cells["date"].dt.year
    cells["subperiod"] = _subperiod(cells["date"], detail)
    year_totals = cells.groupby("year")["arrivals"].transform("sum")
    cells["share"] = (cells["arrivals"] / year_totals * 100).astype("Float64")
    return cells.loc[:, columns].reset_index(drop=True)


def market_share(
    filtered: pd.DataFrame, market: str | None, detail: str
) -> pd.DataFrame:
    """Calcula el peso de cada grupo de origen dentro de los mercados filtrados.

    Con todos los mercados se comparan regiones; con una región, sus orígenes.
    """
    columns = ["group", "period_key", "date", "label", "arrivals", "share"]
    if filtered.empty or not isinstance(market, str) or market.startswith("origin:"):
        return pd.DataFrame(columns=columns)
    group = "origin_region" if market == "all" else "origin"
    frequency = FREQUENCIES[detail]
    periods = filtered["date"].dt.to_period(frequency)
    totals = (
        filtered.groupby([filtered[group], periods], sort=True)["arrivals"]
        .sum()
        .rename_axis(["group", "period"])
        .reset_index()
    )
    period_totals = totals.groupby("period")["arrivals"].transform("sum")
    totals["share"] = (totals["arrivals"] / period_totals * 100).astype("Float64")
    totals["period_key"] = totals["period"].astype(str)
    totals["date"] = totals["period"].dt.start_time
    totals["label"] = [period_label(period, detail) for period in totals["period"]]
    order = {name: index for index, name in enumerate(filtered[group].unique())}
    totals["_order"] = totals["group"].map(order)
    totals = totals.sort_values(["_order", "date"], kind="stable")
    return totals.loc[:, columns].reset_index(drop=True)


def drillable_regions(arrivals: pd.DataFrame) -> set[str]:
    origins = arrivals.groupby("origin_region")["origin"].nunique()
    return set(origins.loc[origins > 1].index)


def aggregate_occupancy(
    occupancy: pd.DataFrame,
    start_date: str | None,
    end_date: str | None,
    detail: str,
) -> pd.DataFrame:
    """Calcula la ocupación de cada periodo como ocupadas entre disponibles."""
    columns = [
        "period_key",
        "date",
        "label",
        "rooms_available",
        "rooms_occupied",
        "occupancy_rate",
        "months",
    ]
    start = pd.to_datetime(start_date, errors="coerce")
    end = pd.to_datetime(end_date, errors="coerce")
    if occupancy.empty or pd.isna(start) or pd.isna(end) or start > end:
        return pd.DataFrame(columns=columns)
    rows = occupancy.loc[occupancy["date"].between(start, end)]
    if rows.empty:
        return pd.DataFrame(columns=columns)
    periods = rows["date"].dt.to_period(FREQUENCIES[detail])
    grouped = rows.groupby(periods, sort=True)
    result = grouped[["rooms_available", "rooms_occupied"]].sum()
    result = result.rename_axis("period").reset_index()
    result["months"] = grouped["date"].nunique().to_numpy()
    result["occupancy_rate"] = (
        result["rooms_occupied"] / result["rooms_available"] * 100
    ).astype("Float64")
    result["period_key"] = result["period"].astype(str)
    result["date"] = result["period"].dt.start_time
    result["label"] = [period_label(period, detail) for period in result["period"]]
    return result.loc[:, columns]


def make_season_selection(
    event: Mapping[str, Any] | None, detail: str
) -> dict[str, str | None]:
    """Valida el periodo elegido en la estacionalidad o en la ocupación."""
    selection: dict[str, str | None] = {"period": None, "detail": detail}
    if not isinstance(event, Mapping) or not isinstance(event.get("points"), list):
        return selection
    for point in event["points"]:
        custom = point.get("customdata") if isinstance(point, Mapping) else None
        if not isinstance(custom, (list, tuple)) or not custom:
            continue
        key = custom[0]
        if not isinstance(key, str) or detail not in FREQUENCIES:
            continue
        try:
            period = pd.Period(key, freq=FREQUENCIES[detail])
        except ValueError:
            continue
        if str(period) == key:
            selection["period"] = key
            return selection
    return selection


def heatmap_event(event: Mapping[str, Any] | None, detail: str) -> dict | None:
    """Traduce el clic del mapa de calor, que solo trae columna y año, a su periodo.

    Plotly no incluye customdata en los clics de un mapa de calor.
    """
    if not isinstance(event, Mapping) or not isinstance(event.get("points"), list):
        return None
    points = []
    for point in event["points"]:
        if not isinstance(point, Mapping):
            continue
        column, year = point.get("x"), point.get("y")
        if not isinstance(column, int) or not isinstance(year, int):
            continue
        if detail == "month":
            key = f"{year}-{column + 1:02d}"
        elif detail == "quarter":
            key = f"{year}Q{column + 1}"
        else:
            key = str(year)
        points.append({"customdata": [key]})
    return {"points": points}


def season_selection_label(selection: Mapping[str, Any] | None) -> str:
    key = selection.get("period") if isinstance(selection, Mapping) else None
    if not key:
        return "Sin periodo elegido. Haz clic en una celda o en una barra para comparar ambas gráficas."
    period = pd.Period(key, freq=FREQUENCIES[selection["detail"]])
    return "Periodo elegido: " + period_label(period, selection["detail"])


def share_caption(market: str | None, labels: Mapping[str, str]) -> str:
    if market == "all":
        return "Nivel: todas las regiones"
    if isinstance(market, str) and market.startswith("region:"):
        return f"Nivel: países de {display_origin(market.split(':', 1)[1])}"
    return "Nivel: " + labels.get(market, "mercado sin desglose")
