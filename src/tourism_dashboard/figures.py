from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tourism_dashboard.exploration import (
    SUBPERIOD_LABELS,
    aggregate_arrivals,
    aggregate_markets,
    display_origin,
    month_label,
)
from tourism_dashboard.models import model_errors

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
SEQUENTIAL_BLUES = ["#E8F1F8", "#BBD5EA", "#7FB0D6", "#3F86BD", "#0B5C8E", "#0B3C5D"]
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
    figure.update_xaxes(**_spanish_ticks(totals["date"], detail))
    return figure


def _spanish_ticks(dates: pd.Series, detail: str) -> dict:
    """Etiquetas en español, sin depender del idioma del navegador."""
    step = max(1, (len(dates) + 7) // 8)
    ticks = dates.iloc[::step]
    if detail == "month":
        ticktext = [f"{date.month:02d}/{date.year}" for date in ticks]
    elif detail == "quarter":
        ticktext = [f"T{date.quarter} {date.year}" for date in ticks]
    else:
        ticktext = ticks.dt.strftime("%Y").tolist()
    return {"tickmode": "array", "tickvals": ticks.tolist(), "ticktext": ticktext}


def _show_no_data(figure: go.Figure, message: str) -> go.Figure:
    figure.add_annotation(
        text=message,
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
            text="No hay resultados para este modelo.<br>Elige uno de los tres modelos en el selector de arriba.",
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


SHARE_NO_DATA_MESSAGE = (
    "Con un solo mercado su peso siempre es 100 %.<br>"
    "Elige «Todos los mercados» o una región para comparar."
)
OCCUPANCY_NO_DATA_MESSAGE = (
    "No hay ocupación hotelera en este periodo.<br>"
    "INGUAT la publica de enero de 2022 a diciembre de 2024: "
    "amplía el periodo para incluir esos años."
)


def seasonality_figure(
    cells: pd.DataFrame, detail: str, mode: str, selected_key: str | None
) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 60, "r": 24, "t": 24, "b": 50},
        height=460,
        separators=",.",
        hovermode="closest",
        dragmode=False,
        xaxis={
            "title": None,
            "showgrid": False,
            "zeroline": False,
            "side": "top",
            "fixedrange": True,
        },
        yaxis={
            "title": "Año",
            "showgrid": False,
            "zeroline": False,
            "autorange": "reversed",
            "dtick": 1,
            "fixedrange": True,
        },
    )
    if cells.empty:
        return _show_no_data(figure, NO_DATA_MESSAGE)

    labels = SUBPERIOD_LABELS[detail]
    years = list(range(int(cells["year"].min()), int(cells["year"].max()) + 1))
    indexed = cells.set_index(["year", "subperiod"])
    is_share = mode == "share" and detail != "year"
    value_column = "share" if is_share else "arrivals"
    z, custom = [], []
    for year in years:
        z_row, custom_row = [], []
        for subperiod in range(1, len(labels) + 1):
            if (year, subperiod) in indexed.index:
                cell = indexed.loc[(year, subperiod)]
                z_row.append(float(cell[value_column]))
                custom_row.append(
                    [
                        cell["period_key"],
                        cell["label"],
                        _spanish_number(float(cell["arrivals"])),
                        _spanish_number(float(cell["share"]), 1),
                        int(cell["months"]),
                    ]
                )
            else:
                # Los meses sin dato quedan en blanco; no se rellenan con ceros.
                z_row.append(None)
                custom_row.append(["", "Sin datos", "—", "—", 0])
        z.append(z_row)
        custom.append(custom_row)

    figure.add_trace(
        go.Heatmap(
            x=list(range(len(labels))),
            y=years,
            z=z,
            customdata=custom,
            colorscale=[
                [index / (len(SEQUENTIAL_BLUES) - 1), color]
                for index, color in enumerate(SEQUENTIAL_BLUES)
            ],
            # En «% del año» la pandemia deja valores extremos; se saturan para
            # que el resto de los años conserve contraste.
            zmin=float(cells[value_column].min()) if is_share else 0,
            zmax=float(cells[value_column].quantile(0.95)) if is_share else None,
            xgap=2,
            ygap=2,
            hoverongaps=False,
            name="Llegadas observadas",
            colorbar={
                "title": {"text": "% del año" if is_share else "Llegadas"},
                "ticksuffix": " %" if is_share else "",
                "tickformat": ",.0f",
                "thickness": 14,
            },
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Llegadas observadas: %{customdata[2]}<br>"
                "Peso dentro del año: %{customdata[3]} %<br>"
                "Meses con información: %{customdata[4]}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(
        tickmode="array", tickvals=list(range(len(labels))), ticktext=labels
    )
    selected = cells.loc[cells["period_key"] == selected_key]
    if not selected.empty:
        cell = selected.iloc[0]
        column = int(cell["subperiod"]) - 1
        figure.add_shape(
            type="rect",
            x0=column - 0.5,
            x1=column + 0.5,
            y0=int(cell["year"]) - 0.5,
            y1=int(cell["year"]) + 0.5,
            line={"color": TEXT, "width": 3},
        )
    return figure


def market_share_figure(
    shares: pd.DataFrame, detail: str, drillable: set[str]
) -> go.Figure:
    groups = list(dict.fromkeys(shares["group"])) if not shares.empty else []
    titles = [display_origin(group) for group in groups] or [""]
    figure = make_subplots(
        rows=1,
        cols=max(1, len(groups)),
        shared_yaxes=True,
        horizontal_spacing=0.025,
        subplot_titles=titles,
    )
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 70, "r": 24, "t": 48, "b": 50},
        height=360,
        separators=",.",
        hovermode="closest",
        dragmode="zoom",
        showlegend=False,
    )
    figure.update_annotations(font={"size": 13, "color": TEXT})
    if shares.empty:
        return _show_no_data(figure, SHARE_NO_DATA_MESSAGE)

    maximum = float(shares["share"].max())
    for column, group in enumerate(groups, start=1):
        # Cada panel resalta un grupo y deja los demás en gris como contexto.
        for other in groups:
            if other == group:
                continue
            rows = shares.loc[shares["group"] == other]
            figure.add_trace(
                go.Scatter(
                    x=rows["date"].tolist(),
                    y=rows["share"].astype(float).tolist(),
                    mode="lines",
                    line={"color": CONTEXT, "width": 1},
                    opacity=0.45,
                    hoverinfo="skip",
                ),
                row=1,
                col=column,
            )
        rows = shares.loc[shares["group"] == group]
        can_drill = group in drillable
        figure.add_trace(
            go.Scatter(
                x=rows["date"].tolist(),
                y=rows["share"].astype(float).tolist(),
                name=display_origin(group),
                mode="lines+markers" if detail == "year" else "lines",
                line={"color": OBSERVED, "width": 2.5},
                marker={"color": OBSERVED, "size": 6},
                customdata=[
                    [
                        group,
                        label,
                        _spanish_number(float(arrivals)),
                        _spanish_number(float(share), 1),
                        "Haz clic para ver sus países" if can_drill else "",
                    ]
                    for label, arrivals, share in zip(
                        rows["label"], rows["arrivals"], rows["share"]
                    )
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                    "Peso en las llegadas: %{customdata[3]} %<br>"
                    "Llegadas observadas: %{customdata[2]}<br>"
                    "%{customdata[4]}<extra></extra>"
                ),
            ),
            row=1,
            col=column,
        )
    figure.update_xaxes(
        showgrid=False,
        tickformat="%Y",
        nticks=4,
        automargin=True,
        ticklabelstandoff=8,
    )
    figure.update_yaxes(
        gridcolor=GRID,
        zeroline=False,
        range=[0, maximum * 1.1],
        ticksuffix=" %",
        tickformat=",.0f",
        ticklabelstandoff=8,
    )
    figure.update_yaxes(title="% de las llegadas", row=1, col=1)
    return figure


def occupancy_figure(
    rows: pd.DataFrame, detail: str, selected_key: str | None
) -> go.Figure:
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
        dragmode=False,
        showlegend=False,
        xaxis={
            "title": "Periodo",
            "showgrid": False,
            "automargin": True,
            "ticklabelstandoff": 8,
        },
        yaxis={
            "title": "Habitaciones ocupadas (%)",
            "gridcolor": GRID,
            "zeroline": False,
            "range": [0, 100],
            "ticksuffix": " %",
            "automargin": True,
            "fixedrange": True,
            "ticklabelstandoff": 10,
        },
    )
    if rows.empty:
        return _show_no_data(figure, OCCUPANCY_NO_DATA_MESSAGE)

    is_highlighted = selected_key in set(rows["period_key"])
    colors = [
        OBSERVED if not is_highlighted or key == selected_key else CONTEXT
        for key in rows["period_key"]
    ]
    figure.add_trace(
        go.Bar(
            x=rows["date"].tolist(),
            y=rows["occupancy_rate"].astype(float).tolist(),
            name="Ocupación observada",
            marker={"color": colors},
            customdata=[
                [
                    key,
                    label,
                    _spanish_number(float(occupied)),
                    _spanish_number(float(available)),
                    int(months),
                ]
                for key, label, occupied, available, months in zip(
                    rows["period_key"],
                    rows["label"],
                    rows["rooms_occupied"],
                    rows["rooms_available"],
                    rows["months"],
                )
            ],
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Ocupación observada: %{y:.1f} %<br>"
                "Habitaciones ocupadas: %{customdata[2]} de %{customdata[3]}<br>"
                "Meses con información: %{customdata[4]}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(**_spanish_ticks(rows["date"], detail))
    if selected_key and not is_highlighted:
        figure.add_annotation(
            text="El periodo elegido no tiene ocupación publicada; INGUAT la reporta de 2022 a 2024.",
            x=0,
            y=1.06,
            xref="paper",
            yref="paper",
            xanchor="left",
            showarrow=False,
            font={"size": 13, "color": SECONDARY},
        )
    return figure


def arrivals_occupancy_figure(
    rows: pd.DataFrame, detail: str, selected_key: str | None
) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 70, "r": 24, "t": 40, "b": 65},
        height=420,
        separators=",.",
        hovermode="closest",
        dragmode="zoom",
        showlegend=False,
        xaxis={
            "title": "Llegadas del mercado elegido (viajeros)",
            "ticklabelstandoff": 8,
            "gridcolor": GRID,
            "rangemode": "tozero",
            "tickformat": ",.0f",
            "automargin": True,
        },
        yaxis={
            "title": "Ocupación hotelera nacional (%)",
            "gridcolor": GRID,
            "range": [0, 100],
            "ticksuffix": " %",
            "automargin": True,
            "ticklabelstandoff": 10,
        },
    )
    if rows.empty:
        return _show_no_data(
            figure,
            "No hay meses con información de ambas fuentes.<br>"
            "Elige un periodo entre 2022 y 2024 y un mercado con datos.",
        )
    highlighted = selected_key in set(rows["period_key"])
    colors = [
        OBSERVED if not highlighted or key == selected_key else CONTEXT
        for key in rows["period_key"]
    ]
    figure.add_trace(
        go.Scatter(
            x=rows["arrivals"].astype(float).tolist(),
            y=rows["occupancy_rate"].astype(float).tolist(),
            mode="markers",
            name="Datos observados",
            marker={"color": colors, "size": 11, "symbol": "circle"},
            customdata=[
                [key, label, int(months), float(occupied), float(available)]
                for key, label, months, occupied, available in zip(
                    rows["period_key"],
                    rows["label"],
                    rows["months"],
                    rows["rooms_occupied"],
                    rows["rooms_available"],
                )
            ],
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>Llegadas observadas: %{x:,.0f}<br>"
                "Ocupación nacional: %{y:.1f} %<br>Meses en común: %{customdata[2]}<br>"
                "Habitaciones ocupadas: %{customdata[3]:,.0f} de %{customdata[4]:,.0f}<extra></extra>"
            ),
        )
    )
    if selected_key and not highlighted:
        figure.add_annotation(
            text="El periodo elegido no tiene datos comunes a ambas fuentes.",
            x=0,
            y=1.06,
            xref="paper",
            yref="paper",
            xanchor="left",
            showarrow=False,
            font={"size": 13, "color": SECONDARY},
        )
    return figure


def model_errors_figure(predictions: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        template="none",
        font={"family": FONT_FAMILY, "size": 13, "color": TEXT},
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        margin={"l": 80, "r": 24, "t": 45, "b": 65},
        height=420,
        separators=",.",
        hovermode="closest",
        dragmode="zoom",
        showlegend=False,
        xaxis={"title": "Mes evaluado", "showgrid": False, "automargin": True},
        yaxis={
            "title": "Error de estimación (viajeros)",
            "gridcolor": GRID,
            "zeroline": False,
            "tickformat": ",.0f",
            "automargin": True,
        },
    )
    if predictions.empty:
        return _show_no_data(
            figure,
            "No hay resultados para un modelo válido.<br>Elige un modelo en el selector de esta vista.",
        )
    rows = model_errors(predictions)
    label = str(rows.iloc[0]["model_label"])
    figure.add_trace(
        go.Bar(
            x=rows["date"].tolist(),
            y=rows["error"].astype(float).tolist(),
            name=f"Error · {label}",
            marker={"color": ESTIMATED},
            customdata=[
                [
                    month_label(date),
                    float(observed),
                    float(estimate),
                    "Sobreestimación"
                    if error > 0
                    else "Subestimación"
                    if error < 0
                    else "Sin error",
                ]
                for date, observed, estimate, error in zip(
                    rows["date"],
                    rows["observed"],
                    rows["estimate"],
                    rows["error"],
                )
            ],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Observado: %{customdata[1]:,.0f}<br>"
                "Estimado: %{customdata[2]:,.0f}<br>Error: %{y:,.0f} viajeros<br>"
                "%{customdata[3]}<extra></extra>"
            ),
        )
    )
    figure.add_hline(y=0, line_color=TEXT, line_width=1)
    figure.update_xaxes(**_spanish_ticks(rows["date"], "month"))
    figure.add_annotation(
        text=f"Error = estimado − observado · {label}",
        x=0,
        y=1.08,
        xref="paper",
        yref="paper",
        xanchor="left",
        showarrow=False,
        font={"size": 13, "color": SECONDARY},
    )
    return figure
