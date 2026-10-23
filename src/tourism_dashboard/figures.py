from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from tourism_dashboard.exploration import (
    aggregate_arrivals,
    aggregate_markets,
    display_origin,
)

NO_DATA_MESSAGE = (
    "No hay información para esta selección.<br>"
    "Prueba con un periodo más amplio, elige «Todos los mercados» "
    "o limpia la selección."
)
ORIGIN_TYPES = {"country": "País", "region": "Agregado", "segment": "Segmento"}
OBSERVED = "#0B5C8E"
ESTIMATED = "#D55E00"
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
            text=NO_DATA_MESSAGE,
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
                float(value) if pd.notna(value) else None
                for value in plotted["arrivals"]
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


def _spanish_number(value: float, decimals: int = 0) -> str:
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def markets_figure(rows: pd.DataFrame) -> go.Figure:
    markets = aggregate_markets(rows)
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 20, "r": 24, "t": 40, "b": 65},
        height=400,
        separators=",.",
        hovermode="closest",
        dragmode=False,
        showlegend=False,
        xaxis={
            "title": "Llegadas de visitantes",
            "gridcolor": GRID,
            "zeroline": False,
            "tickformat": ",.0f",
            "automargin": True,
        },
        yaxis={
            "autorange": "reversed",
            "automargin": True,
            "showgrid": False,
            "tickfont": {"size": 13},
        },
    )
    if markets.empty:
        figure.add_annotation(
            text=NO_DATA_MESSAGE,
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

    names = [display_origin(origin) for origin in markets["origin"]]
    figure.add_trace(
        go.Bar(
            x=markets["arrivals"].tolist(),
            y=names,
            orientation="h",
            name="Llegadas observadas",
            marker={"color": OBSERVED},
            text=[
                f"{_spanish_number(arrivals)} · {_spanish_number(share, 1)} %"
                for arrivals, share in zip(markets["arrivals"], markets["share"])
            ],
            textposition="outside",
            cliponaxis=False,
            textfont={"size": 13, "color": TEXT},
            customdata=[
                [ORIGIN_TYPES[level], _spanish_number(share, 1)]
                for level, share in zip(markets["origin_level"], markets["share"])
            ],
            hovertemplate=(
                "<b>%{y}</b> (%{customdata[0]})<br>"
                "Llegadas observadas: %{x:,.0f}<br>"
                "Participación en la selección: %{customdata[1]} %<extra></extra>"
            ),
        )
    )
    # Deja espacio a la derecha para que la etiqueta de la barra más larga se lea completa.
    figure.update_xaxes(range=[0, markets["arrivals"].max() * 1.55])
    return figure


def model_evaluation_figure(predictions: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 70, "r": 24, "t": 32, "b": 65},
        height=420,
        separators=",.",
        hovermode="x unified",
        legend={"orientation": "h", "x": 0, "y": 1.12},
        xaxis={"title": "Mes de evaluación", "showgrid": False, "automargin": True},
        yaxis={
            "title": "Turistas y excursionistas",
            "gridcolor": GRID,
            "rangemode": "tozero",
            "tickformat": ",.0f",
            "automargin": True,
        },
    )
    if predictions.empty:
        figure.add_annotation(
            text="No hay resultados para el modelo seleccionado.",
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

    rows = predictions.sort_values("date", kind="stable")
    label = str(rows.iloc[0]["model_label"])
    figure.add_trace(
        go.Scatter(
            x=rows["date"].tolist(),
            y=rows["observed"].astype(float).tolist(),
            name="Observado",
            mode="lines",
            line={"color": OBSERVED, "width": 2.5, "dash": "solid"},
            hovertemplate="Observado: %{y:,.0f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=rows["date"].tolist(),
            y=rows["estimate"].astype(float).tolist(),
            name=f"Estimado · {label}",
            mode="lines",
            line={"color": ESTIMATED, "width": 2.5, "dash": "dash"},
            hovertemplate="Estimado: %{y:,.0f}<extra></extra>",
        )
    )
    return figure
