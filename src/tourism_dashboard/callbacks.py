from __future__ import annotations

import pandas as pd
from dash import Dash, Input, Output, ctx

from tourism_dashboard.exploration import (
    DETAIL_OPTIONS,
    aggregate_arrivals,
    apply_selection,
    filter_arrivals,
    make_selection,
    market_labels,
    markets_caption,
    month_label,
    selection_label,
)
from tourism_dashboard.figures import (
    arrivals_figure,
    markets_figure,
    model_evaluation_figure,
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
        disabled = active_tab != "arrivals"
        options = [dict(option, disabled=disabled) for option in DETAIL_OPTIONS]
        note = (
            "Los filtros se aplican a la vista Llegadas y mercados." if disabled else ""
        )
        hidden = tuple(
            active_tab != tab for tab in ("arrivals", "seasons", "models", "data")
        )
        return *hidden, disabled, disabled, disabled, options, note
