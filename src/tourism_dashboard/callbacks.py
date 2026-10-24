from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, ctx, no_update

from tourism_dashboard.exploration import (
    DETAIL_OPTIONS,
    SEASONALITY_MODES,
    aggregate_arrivals,
    aggregate_occupancy,
    apply_selection,
    drillable_regions,
    filter_arrivals,
    heatmap_event,
    make_season_selection,
    make_selection,
    market_labels,
    market_share,
    markets_caption,
    month_label,
    season_selection_label,
    seasonal_cells,
    selection_label,
    share_caption,
)
from tourism_dashboard.figures import (
    arrivals_figure,
    market_share_figure,
    markets_figure,
    model_evaluation_figure,
    occupancy_figure,
    seasonality_figure,
)
from tourism_dashboard.models import (
    metric_values,
    model_status,
    sanitize_model_selection,
    selected_model_rows,
)


def _number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


def summary_values(filtered: pd.DataFrame) -> tuple[str, str, str, str]:
    if filtered.empty:
        return "—", "—", "Sin información en este periodo", "0"
    monthly = aggregate_arrivals(filtered, "month")
    peak = float(monthly["arrivals"].max())
    peak_months = monthly.loc[monthly["arrivals"] == peak, "date"]
    label = "; ".join(month_label(date) for date in peak_months)
    return (
        _number(float(monthly["arrivals"].sum())),
        _number(peak),
        label,
        str(len(monthly)),
    )


def register_callbacks(
    app: Dash,
    arrivals: pd.DataFrame,
    model_predictions: pd.DataFrame,
    model_metrics: pd.DataFrame,
    occupancy: pd.DataFrame,
) -> None:
    @app.callback(
        Output("arrivals-timeline", "figure"),
        Output("arrivals-timeline", "clickData"),
        Output("arrivals-timeline", "selectedData"),
        Output("arrivals-total", "children"),
        Output("peak-arrivals", "children"),
        Output("peak-month", "children"),
        Output("covered-months", "children"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("origin-filter", "value"),
        Input("time-detail", "value"),
        Input("clear-selection", "n_clicks"),
    )
    def update_timeline(start_date, end_date, market, detail, reset_count):
        filtered = filter_arrivals(arrivals, start_date, end_date, market)
        revision = f"{start_date}|{end_date}|{market}|{detail}|{reset_count}"
        return (
            arrivals_figure(filtered, detail, revision),
            None,
            None,
            *summary_values(filtered),
        )

    @app.callback(
        Output("v1-selection", "data"),
        Output("selection-label", "children"),
        Output("clear-selection", "disabled"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("origin-filter", "value"),
        Input("time-detail", "value"),
        Input("arrivals-timeline", "selectedData"),
        Input("arrivals-timeline", "clickData"),
        Input("clear-selection", "n_clicks"),
    )
    def update_selection(
        start_date, end_date, market, detail, selected_data, click_data, _reset_count
    ):
        filtered = filter_arrivals(arrivals, start_date, end_date, market)
        triggers = ctx.triggered_prop_ids
        filter_ids = {
            "period-start.value",
            "period-end.value",
            "origin-filter.value",
            "time-detail.value",
            "clear-selection.n_clicks",
        }
        event = None
        if not filter_ids.intersection(triggers):
            if "arrivals-timeline.selectedData" in triggers:
                event = selected_data
            elif "arrivals-timeline.clickData" in triggers:
                event = click_data
        selection = make_selection(filtered, market, detail, event)
        return selection, selection_label(selection), not selection["is_selected"]

    labels = market_labels(arrivals)

    @app.callback(
        Output("market-chart", "figure"),
        Output("market-caption", "children"),
        Input("v1-selection", "data"),
    )
    def update_markets(selection):
        if not isinstance(selection, dict):
            selection = {"dates": [], "market": None, "is_selected": False}
        rows = apply_selection(arrivals, selection)
        return markets_figure(rows), markets_caption(selection, labels)

    drillable = drillable_regions(arrivals)

    @app.callback(
        Output("market-share-chart", "figure"),
        Output("market-share-caption", "children"),
        Output("market-share-back", "disabled"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("origin-filter", "value"),
        Input("time-detail", "value"),
    )
    def update_market_share(start_date, end_date, market, detail):
        filtered = filter_arrivals(arrivals, start_date, end_date, market)
        shares = market_share(filtered, market, detail)
        return (
            market_share_figure(shares, detail, drillable),
            share_caption(market, labels),
            market == "all",
        )

    @app.callback(
        Output("origin-filter", "value"),
        Output("market-share-chart", "clickData"),
        Input("market-share-chart", "clickData"),
        Input("market-share-back", "n_clicks"),
        Input("origin-filter", "value"),
    )
    def drill_markets(click_data, _back_count, market):
        # Bajar de nivel solo es posible desde las regiones con varios países.
        if ctx.triggered_id == "market-share-back":
            return "all", None
        if ctx.triggered_id != "market-share-chart" or market != "all":
            return no_update, None
        points = click_data.get("points") if isinstance(click_data, dict) else None
        for point in points or []:
            custom = point.get("customdata") if isinstance(point, dict) else None
            if isinstance(custom, list) and custom and custom[0] in drillable:
                return f"region:{custom[0]}", None
        return no_update, None

    @app.callback(
        Output("season-selection", "data"),
        Output("seasonality-chart", "clickData"),
        Output("occupancy-chart", "clickData"),
        Output("season-selection-label", "children"),
        Output("clear-season-selection", "disabled"),
        Input("seasonality-chart", "clickData"),
        Input("occupancy-chart", "clickData"),
        Input("clear-season-selection", "n_clicks"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("origin-filter", "value"),
        Input("time-detail", "value"),
    )
    def update_season_selection(
        seasonality_click, occupancy_click, _reset, _start, _end, _market, detail
    ):
        event = None
        if ctx.triggered_id == "seasonality-chart":
            event = heatmap_event(seasonality_click, detail)
        elif ctx.triggered_id == "occupancy-chart":
            event = occupancy_click
        selection = make_season_selection(event, detail)
        return (
            selection,
            None,
            None,
            season_selection_label(selection),
            selection["period"] is None,
        )

    @app.callback(
        Output("seasonality-chart", "figure"),
        Output("seasonality-mode", "options"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("origin-filter", "value"),
        Input("time-detail", "value"),
        Input("seasonality-mode", "value"),
        Input("season-selection", "data"),
    )
    def update_seasonality(start_date, end_date, market, detail, mode, selection):
        filtered = filter_arrivals(arrivals, start_date, end_date, market)
        selected = selection.get("period") if isinstance(selection, dict) else None
        # Con detalle anual cada año es el 100 % de sí mismo.
        options = [
            dict(option, disabled=detail == "year" and option["value"] == "share")
            for option in SEASONALITY_MODES
        ]
        return (
            seasonality_figure(seasonal_cells(filtered, detail), detail, mode, selected),
            options,
        )

    @app.callback(
        Output("occupancy-chart", "figure"),
        Input("period-start", "value"),
        Input("period-end", "value"),
        Input("time-detail", "value"),
        Input("season-selection", "data"),
    )
    def update_occupancy(start_date, end_date, detail, selection):
        rows = aggregate_occupancy(occupancy, start_date, end_date, detail)
        selected = selection.get("period") if isinstance(selection, dict) else None
        return occupancy_figure(rows, detail, selected)

    @app.callback(
        Output("v7-model-selection", "data"),
        Input("model-selector", "value"),
    )
    def update_model_selection(model_id):
        return sanitize_model_selection(
            model_id, model_predictions, model_metrics
        )

    @app.callback(
        Output("model-evaluation-chart", "figure"),
        Output("model-mae", "children"),
        Output("model-rmse", "children"),
        Output("model-mape", "children"),
        Output("model-status", "children"),
        Input("v7-model-selection", "data"),
    )
    def update_model_evaluation(selection):
        predictions, metrics = selected_model_rows(
            model_predictions, model_metrics, selection
        )
        mae, rmse, mape = metric_values(metrics)
        return (
            model_evaluation_figure(predictions),
            mae,
            rmse,
            mape,
            model_status(metrics),
        )

    @app.callback(
        Output("arrivals-panel", "hidden"),
        Output("seasons-panel", "hidden"),
        Output("models-panel", "hidden"),
        Output("data-panel", "hidden"),
        Output("period-start", "disabled"),
        Output("period-end", "disabled"),
        Output("origin-filter", "disabled"),
        Output("time-detail", "options"),
        Output("filter-note", "children"),
        Input("main-tabs", "active_tab"),
    )
    def switch_tab(active_tab):
        disabled = active_tab not in {"arrivals", "seasons"}
        options = [dict(option, disabled=disabled) for option in DETAIL_OPTIONS]
        if disabled:
            note = "Los filtros se aplican a las vistas Llegadas y mercados y Temporadas y hospedaje."
        elif active_tab == "seasons":
            note = "El mercado de origen cambia la estacionalidad; la ocupación hotelera es nacional y no depende de él."
        else:
            note = ""
        hidden = tuple(
            active_tab != tab for tab in ("arrivals", "seasons", "models", "data")
        )
        return *hidden, disabled, disabled, disabled, options, note
