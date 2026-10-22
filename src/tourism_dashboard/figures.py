from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from tourism_dashboard.exploration import aggregate_arrivals

OBSERVED = "#0B5C8E"
CONTEXT = "#8A939E"
TEXT = "#1F2933"
SECONDARY = "#5B6573"
GRID = "#E3E6EA"
FONT_FAMILY = "Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"


def arrivals_figure(filtered: pd.DataFrame, detail: str, revision: str) -> go.Figure:
    totals = aggregate_arrivals(filtered, detail)
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 70, "r": 24, "t": 32, "b": 65},
        height=400,
        separators=",.",
        hovermode="closest",
        clickmode="event+select",
        dragmode="select",
        selectdirection="h",
        uirevision=revision,
        selectionrevision=revision,
        legend={"orientation": "h", "x": 0, "y": 1.12},
        xaxis={
            "title": "Periodo",
            "showgrid": False,
            "zeroline": False,
            "automargin": True,
        },
        yaxis={
            "title": "Llegadas de visitantes",
            "gridcolor": GRID,
            "zeroline": False,
            "rangemode": "tozero",
            "tickformat": ",.0f",
            "automargin": True,
        },
    )
    if totals.empty:
        figure.add_annotation(
            text="No hay información para esta selección.<br>Revisa el periodo y el mercado de origen.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 15, "color": SECONDARY},
        )
        figure.update_xaxes(visible=False)
        figure.update_yaxes(visible=False)
        return figure

    # Los huecos de la fuente interrumpen la línea; no se convierten en ceros.
    complete_periods = pd.period_range(
        totals["period"].min(), totals["period"].max(), freq=totals["period"].dtype.freq
    )
    plotted = totals.set_index("period").reindex(complete_periods)
    labels = [label if isinstance(label, str) else "" for label in plotted["label"]]
    custom = [
        [str(period), label, int(months) if pd.notna(months) else 0]
        for period, label, months in zip(plotted.index, labels, plotted["months"])
    ]
    figure.add_trace(
        go.Scatter(
            x=plotted.index.start_time.to_list(),
            y=[
                int(value) if pd.notna(value) else None for value in plotted["arrivals"]
            ],
            name="Llegadas observadas",
            mode="lines+markers",
            connectgaps=False,
            line={"color": OBSERVED, "width": 2.5},
            marker={"color": OBSERVED, "size": 8},
            selected={"marker": {"color": OBSERVED, "size": 11, "opacity": 1}},
            unselected={"marker": {"color": CONTEXT, "opacity": 0.6}},
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Llegadas observadas: %{y:,.0f}<br>"
                "Meses con información: %{customdata[2]}<extra></extra>"
            ),
        )
    )
    # Etiquetas en español, sin depender del idioma del navegador.
    step = max(1, (len(totals) + 7) // 8)
    ticks = totals.iloc[::step]
    if detail == "month":
        ticktext = [f"{date.month:02d}/{date.year}" for date in ticks["date"]]
    elif detail == "quarter":
        ticktext = [f"T{date.quarter} {date.year}" for date in ticks["date"]]
    else:
        ticktext = ticks["date"].dt.strftime("%Y").tolist()
    figure.update_xaxes(
        tickmode="array", tickvals=ticks["date"].tolist(), ticktext=ticktext
    )
    return figure
