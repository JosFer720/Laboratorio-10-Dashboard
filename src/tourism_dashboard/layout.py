from __future__ import annotations

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

from tourism_dashboard.exploration import (
    DETAIL_OPTIONS,
    SEASONALITY_MODES,
    aggregate_occupancy,
    apply_selection,
    drillable_regions,
    make_selection,
    market_share,
    market_labels,
    market_options,
    markets_caption,
    month_options,
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
    initial_model_selection,
    metric_values,
    model_options,
    model_status,
    selected_model_rows,
)

GRAPH_CONFIG = {
    "displaylogo": False,
    "displayModeBar": True,
    "locale": "es",
    "modeBarButtonsToRemove": ["lasso2d"],
    "toImageButtonOptions": {"filename": "llegadas_guatemala", "scale": 2},
}
MARKETS_GRAPH_CONFIG = GRAPH_CONFIG | {
    "toImageButtonOptions": {"filename": "llegadas_por_mercado", "scale": 2}
}
SHARE_GRAPH_CONFIG = GRAPH_CONFIG | {
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {"filename": "peso_de_mercados", "scale": 2},
}
SEASONALITY_GRAPH_CONFIG = GRAPH_CONFIG | {
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "zoom2d", "pan2d"],
    "toImageButtonOptions": {"filename": "estacionalidad_llegadas", "scale": 2},
}
OCCUPANCY_GRAPH_CONFIG = GRAPH_CONFIG | {
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {"filename": "ocupacion_hotelera", "scale": 2},
}
MODELS_GRAPH_CONFIG = GRAPH_CONFIG | {
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    "toImageButtonOptions": {"filename": "evaluacion_historica_modelo", "scale": 2},
}
DROPDOWN_LABELS = {
    "select_all": "Seleccionar todos",
    "deselect_all": "Quitar selección",
    "selected_count": "seleccionados",
    "search": "Buscar",
    "clear_search": "Limpiar búsqueda",
    "clear_selection": "Limpiar selección",
    "no_options_found": "No se encontraron opciones",
}


def _filters(arrivals: pd.DataFrame, months: list[dict[str, str]]) -> html.Div:
    start, end = (months[0]["value"], months[-1]["value"])
    return html.Div(
        [
            html.Fieldset(
                [
                    html.Legend("Periodo"),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Desde", htmlFor="period-start"),
                                    dcc.Dropdown(
                                        id="period-start",
                                        options=months,
                                        value=start,
                                        clearable=False,
                                        labels=DROPDOWN_LABELS,
                                    ),
                                ]
                            ),
                            html.Div(
                                [
                                    html.Label("Hasta", htmlFor="period-end"),
                                    dcc.Dropdown(
                                        id="period-end",
                                        options=months,
                                        value=end,
                                        clearable=False,
                                        labels=DROPDOWN_LABELS,
                                    ),
                                ]
                            ),
                        ],
                        className="period-controls",
                    ),
                ],
                className="period-field",
            ),
            html.Div(
                [
                    html.Label(
                        "Mercado de origen",
                        htmlFor="origin-filter",
                        className="filter-title",
                    ),
                    dcc.Dropdown(
                        id="origin-filter",
                        options=market_options(arrivals),
                        value="all",
                        clearable=False,
                        labels=DROPDOWN_LABELS,
                    ),
                    html.P(
                        "Países y regiones agregadas.",
                        className="control-help",
                    ),
                ]
            ),
            html.Fieldset(
                [
                    html.Legend("Detalle temporal"),
                    dcc.RadioItems(
                        id="time-detail",
                        options=DETAIL_OPTIONS,
                        value="month",
                        inline=True,
                        className="detail-control",
                    ),
                ]
            ),
        ],
        className="filter-grid",
    )


def _header(arrivals: pd.DataFrame, months: list[dict[str, str]]) -> html.Header:
    return html.Header(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.P("GUATEMALA · INGUAT", className="eyebrow"),
                            html.H1("Observatorio de turismo sostenible"),
                            html.P(
                                f"Turistas y excursionistas · {months[0]['label']}–{months[-1]['label']} · ocupación hotelera 2022–2024",
                                className="subtitle",
                            ),
                        ]
                    ),
                    html.Span("Datos históricos", className="observed-badge"),
                ],
                className="heading-row",
            ),
            _filters(arrivals, months),
            html.P(id="filter-note", className="control-help", role="status"),
            dbc.Tabs(
                [
                    dbc.Tab(label="Llegadas y mercados", tab_id="arrivals"),
                    dbc.Tab(label="Temporadas y hospedaje", tab_id="seasons"),
                    dbc.Tab(label="Predicciones y modelos", tab_id="models"),
                    dbc.Tab(label="Sobre los datos", tab_id="data"),
                ],
                id="main-tabs",
                active_tab="arrivals",
            ),
        ],
        className="dashboard-header",
    )


def _metrics() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.P("Llegadas del periodo", className="metric-label"),
                    html.P(id="arrivals-total", className="metric-value"),
                    html.P("Suma de los mercados del filtro", className="note"),
                ],
                className="metric-card",
            ),
            html.Div(
                [
                    html.P("Mes con más llegadas", className="metric-label"),
                    html.P(id="peak-arrivals", className="metric-value"),
                    html.P(id="peak-month", className="note"),
                ],
                className="metric-card",
            ),
            html.Div(
                [
                    html.P("Meses con información", className="metric-label"),
                    html.P(id="covered-months", className="metric-value"),
                    html.P("Dentro del periodo y mercado elegidos", className="note"),
                ],
                className="metric-card",
            ),
        ],
        className="metrics-grid",
        **{"aria-live": "polite"},
    )


def _timeline(arrivals: pd.DataFrame, initial: dict) -> html.Section:
    return html.Section(
        [
            html.Div(
                [
                    html.H3("Llegadas de visitantes en el tiempo"),
                    html.Span("Observado", className="observed-badge"),
                ],
                className="chart-heading",
            ),
            html.P(
                "Haz clic en un punto o arrastra un recuadro para seleccionar periodos. Usa la lupa de la gráfica para ampliar y la casa para restaurar la vista.",
                id="timeline-help",
                className="chart-help",
            ),
            dcc.Graph(
                id="arrivals-timeline",
                figure=arrivals_figure(arrivals, "month", "initial"),
                config=GRAPH_CONFIG,
                responsive=True,
                style={"height": "400px"},
            ),
            html.Div(
                [
                    html.P(
                        selection_label(initial), id="selection-label", role="status"
                    ),
                    html.Button(
                        "Limpiar selección",
                        id="clear-selection",
                        n_clicks=0,
                        disabled=True,
                    ),
                ],
                className="selection-bar",
            ),
            html.P(
                "Fuente: base Migración usada en los Laboratorios 1 y 2. Los años y trimestres suman únicamente los meses incluidos en el filtro.",
                className="note chart-source",
            ),
        ],
        className="chart-card",
        **{"aria-describedby": "timeline-help"},
    )


def _markets(arrivals: pd.DataFrame, initial: dict) -> html.Section:
    return html.Section(
        [
            html.Div(
                [
                    html.H3("Llegadas por mercado de origen"),
                    html.Span("Observado", className="observed-badge"),
                ],
                className="chart-heading",
            ),
            html.P(
                "Muestra de dónde vinieron los visitantes en el periodo que elegiste en la gráfica de llegadas. Sirve para saber qué mercados pesan más y a cuáles dirigir la promoción. Se actualiza al seleccionar puntos allá o al cambiar los filtros.",
                id="markets-help",
                className="chart-help",
            ),
            dcc.Graph(
                id="market-chart",
                figure=markets_figure(apply_selection(arrivals, initial)),
                config=MARKETS_GRAPH_CONFIG,
                responsive=True,
                style={"height": "400px"},
            ),
            html.Div(
                html.P(
                    markets_caption(initial, market_labels(arrivals)),
                    id="market-caption",
                    role="status",
                ),
                className="selection-bar",
            ),
            html.P(
                "Fuente: base Migración usada en los Laboratorios 1 y 2. Los porcentajes son la participación de cada origen en la suma de la selección; los agregados reúnen varios países.",
                className="note chart-source",
            ),
        ],
        className="chart-card",
        **{"aria-describedby": "markets-help"},
    )


def _market_share(arrivals: pd.DataFrame) -> html.Section:
    return html.Section(
        [
            html.Div(
                [
                    html.H3("Peso de cada mercado en el tiempo"),
                    html.Span("Observado", className="observed-badge"),
                ],
                className="chart-heading",
            ),
            html.P(
                "Muestra qué porcentaje de las llegadas aporta cada región en cada periodo. Sirve para ver si un mercado gana o pierde importancia y no depender de uno solo. Haz clic en América del Norte o América Central para ver sus países.",
                id="market-share-help",
                className="chart-help",
            ),
            html.Div(
                [
                    html.P(
                        share_caption("all", market_labels(arrivals)),
                        id="market-share-caption",
                        role="status",
                    ),
                    html.Button(
                        "← Todos los mercados",
                        id="market-share-back",
                        n_clicks=0,
                        disabled=True,
                        className="secondary-button",
                    ),
                ],
                className="selection-bar breadcrumb-bar",
            ),
            dcc.Graph(
                id="market-share-chart",
                figure=market_share_figure(
                    market_share(arrivals, "all", "month"),
                    "month",
                    drillable_regions(arrivals),
                ),
                config=SHARE_GRAPH_CONFIG,
                responsive=True,
                style={"height": "360px"},
            ),
            html.P(
                "Fuente: base Migración usada en los Laboratorios 1 y 2. Cada panel resalta un grupo en azul y deja los demás en gris; todos comparten la misma escala. El peso se calcula sobre los mercados del filtro. Desde enero de 2023 la fuente registra cero viajeros en la categoría Guatemala, por lo que el peso de los demás orígenes de América Central sube ese año; ese salto debe leerse con cautela.",
                className="note chart-source",
            ),
        ],
        className="chart-card",
        **{"aria-describedby": "market-share-help"},
    )


def _arrivals_panel(arrivals: pd.DataFrame, initial: dict) -> html.Section:
    return html.Section(
        [
            html.Div(
                [
                    html.H2("¿Cuándo llegan más visitantes?"),
                    html.P(
                        "Compara la afluencia entre periodos para anticipar temporadas altas y bajas y planificar los recursos de atención al visitante.",
                        className="section-description",
                    ),
                ],
                className="section-heading",
            ),
            _metrics(),
            html.Div(
                [
                    _timeline(arrivals, initial),
                    html.Div(_markets(arrivals, initial), id="market-breakdown"),
                ],
                className="chart-row",
            ),
            html.Div(_market_share(arrivals), className="full-row"),
            html.P(
                "Las cifras suman turistas y excursionistas. Por sí solas no miden la ocupación hotelera ni la presión sobre un destino.",
                className="note page-note",
            ),
        ],
        id="arrivals-panel",
    )


def _seasons_panel(arrivals: pd.DataFrame, occupancy: pd.DataFrame) -> html.Section:
    empty_selection = {"period": None, "detail": "month"}
    start = arrivals["date"].min().strftime("%Y-%m-%d")
    end = arrivals["date"].max().strftime("%Y-%m-%d")
    return html.Section(
        [
            html.Div(
                [
                    html.H2("¿Cómo cambian las temporadas y qué tan llenos están los hoteles?"),
                    html.P(
                        "Compara los meses de cada año para ver si las temporadas altas y bajas se repiten, y revisa la ocupación hotelera para saber cuándo la oferta de hospedaje está más cerca de su límite.",
                        className="section-description",
                    ),
                ],
                className="section-heading",
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.H3("Estacionalidad de las llegadas"),
                            html.Span("Observado", className="observed-badge"),
                        ],
                        className="chart-heading",
                    ),
                    html.P(
                        "Cada fila es un año y cada columna un mes, un trimestre o el año completo, según el detalle temporal; el azul más oscuro indica más llegadas. Sirve para reconocer las temporadas altas y comprobar si se repiten cada año. Con «% del año» se compara la forma de la temporada aunque el volumen total cambie. Haz clic en una celda para ver ese periodo en la ocupación hotelera.",
                        id="seasonality-help",
                        className="chart-help",
                    ),
                    html.Fieldset(
                        [
                            html.Legend("Mostrar", className="inline-legend"),
                            dcc.RadioItems(
                                id="seasonality-mode",
                                options=SEASONALITY_MODES,
                                value="arrivals",
                                inline=True,
                                className="detail-control",
                            ),
                        ],
                        className="inline-field",
                    ),
                    dcc.Graph(
                        id="seasonality-chart",
                        figure=seasonality_figure(
                            seasonal_cells(arrivals, "month"), "month", "arrivals", None
                        ),
                        config=SEASONALITY_GRAPH_CONFIG,
                        responsive=True,
                        style={"height": "460px"},
                    ),
                    html.Div(
                        [
                            html.P(
                                season_selection_label(empty_selection),
                                id="season-selection-label",
                                role="status",
                            ),
                            html.Button(
                                "Limpiar selección",
                                id="clear-season-selection",
                                n_clicks=0,
                                disabled=True,
                                className="secondary-button",
                            ),
                        ],
                        className="selection-bar",
                    ),
                    html.P(
                        "Fuente: base Migración usada en los Laboratorios 1 y 2. Las celdas en blanco son meses sin datos. El porcentaje compara cada periodo con la suma de los meses disponibles de su año; en esa vista los valores más extremos, como los primeros meses de 2020, comparten el tono más oscuro.",
                        className="note chart-source",
                    ),
                ],
                className="chart-card",
                **{"aria-describedby": "seasonality-help"},
            ),
            html.Section(
                [
                    html.Div(
                        [
                            html.H3("Ocupación hotelera"),
                            html.Span("Observado", className="observed-badge"),
                        ],
                        className="chart-heading",
                    ),
                    html.P(
                        "Muestra qué porcentaje de las habitaciones de hotel disponibles se ocupó en cada periodo. Sirve para saber cuándo la oferta de hospedaje está cerca de llenarse y cuándo tiene capacidad libre. Haz clic en una barra para ubicar ese periodo en la estacionalidad.",
                        id="occupancy-help",
                        className="chart-help",
                    ),
                    dcc.Graph(
                        id="occupancy-chart",
                        figure=occupancy_figure(
                            aggregate_occupancy(occupancy, start, end, "month"),
                            "month",
                            None,
                        ),
                        config=OCCUPANCY_GRAPH_CONFIG,
                        responsive=True,
                        style={"height": "400px"},
                    ),
                    html.P(
                        "Fuente: boletines anuales de ocupación hotelera de INGUAT, 2022 a 2024. Es una cifra nacional: no cambia con el mercado de origen e incluye huéspedes que viven en Guatemala.",
                        className="note chart-source",
                    ),
                ],
                className="chart-card",
                **{"aria-describedby": "occupancy-help"},
            ),
        ],
        id="seasons-panel",
        hidden=True,
        className="seasons-panel",
    )


def _data_panel(months: list[dict[str, str]]) -> html.Section:
    return html.Section(
        [
            html.H2("Sobre los datos"),
            html.H3("Qué representan las cifras"),
            html.P(
                "La serie mensual suma turistas y excursionistas. Los orígenes combinan países individuales y regiones agregadas; el filtro identifica cada tipo."
            ),
            html.H3("Cobertura y fuente"),
            html.P(
                f"Periodo disponible en esta fuente de llegadas: {months[0]['label']} a {months[-1]['label']}."
            ),
            html.P(
                "Base Migración preparada para los Laboratorios 1 y 2 de series de tiempo, con registros migratorios y estimaciones de flujos terrestres de INGUAT."
            ),
            html.H3("Límites de interpretación"),
            html.P(
                "El tablero conserva los valores decimales de las estimaciones expandidas y no completa meses con valores inventados."
            ),
            html.P(
                "La ocupación hotelera conserva su cobertura de 2022 a 2024 y tiene un alcance distinto al de las llegadas. Una coincidencia entre ambas series no demuestra causalidad."
            ),
            html.H3("Cómo leer la gráfica"),
            html.P(
                "El azul y la línea continua representan datos observados. El gris deja en segundo plano los puntos fuera de una selección. Al cambiar el detalle, se suman las llegadas de los meses disponibles; no se generan datos diarios."
            ),
        ],
        id="data-panel",
        hidden=True,
        className="information-panel",
    )


def _models_panel(
    predictions: pd.DataFrame, metrics: pd.DataFrame
) -> html.Section:
    initial = initial_model_selection(predictions, metrics)
    selected_predictions, selected_metrics = selected_model_rows(
        predictions, metrics, initial
    )
    mae, rmse, mape = metric_values(selected_metrics)
    options = model_options(predictions, metrics)
    return html.Section(
        [
            html.Div(
                [
                    html.H2("Comparación histórica de modelos"),
                    html.P(
                        "Estas son predicciones evaluadas históricamente entre abril de 2021 y junio de 2026; no son un pronóstico futuro.",
                        className="section-description",
                    ),
                ],
                className="section-heading",
            ),
            html.Div(
                [
                    html.Label("Modelo", htmlFor="model-selector", className="filter-title"),
                    dcc.Dropdown(
                        id="model-selector",
                        options=options,
                        value=initial["model"],
                        clearable=False,
                        disabled=not options,
                        labels=DROPDOWN_LABELS,
                    ),
                    html.P(model_status(selected_metrics), id="model-status", role="status", className="control-help"),
                ],
                className="model-control",
            ),
            html.Div(
                [
                    html.Div(
                        [html.P("MAE", className="metric-label"), html.P(mae, id="model-mae", className="metric-value"), html.P("Error absoluto promedio, en viajeros.", className="note")],
                        className="metric-card",
                    ),
                    html.Div(
                        [html.P("RMSE", className="metric-label"), html.P(rmse, id="model-rmse", className="metric-value"), html.P("Da más peso a los errores grandes.", className="note")],
                        className="metric-card",
                    ),
                    html.Div(
                        [html.P("MAPE", className="metric-label"), html.P(mape, id="model-mape", className="metric-value"), html.P("Error porcentual medio.", className="note")],
                        className="metric-card",
                    ),
                ],
                className="metrics-grid model-metrics",
                **{"aria-live": "polite"},
            ),
            html.Section(
                [
                    html.Div(
                        [html.H3("Valores observados y estimados"), html.Span("Evaluación histórica", className="observed-badge")],
                        className="chart-heading",
                    ),
                    dcc.Graph(
                        id="model-evaluation-chart",
                        figure=model_evaluation_figure(selected_predictions),
                        config=MODELS_GRAPH_CONFIG,
                        responsive=True,
                        style={"height": "420px"},
                    ),
                    html.P(
                        "No se muestra intervalo de confianza porque los resultados originales no incluyen uno.",
                        className="note chart-source",
                    ),
                ],
                className="chart-card",
            ),
        ],
        id="models-panel",
        hidden=True,
        className="models-panel",
    )


def build_layout(
    arrivals: pd.DataFrame,
    model_predictions: pd.DataFrame,
    model_metrics: pd.DataFrame,
    occupancy: pd.DataFrame,
) -> dbc.Container:
    months = month_options(arrivals)
    initial = make_selection(arrivals, "all", "month")
    return dbc.Container(
        [
            dcc.Store(id="v1-selection", storage_type="memory", data=initial),
            dcc.Store(
                id="season-selection",
                storage_type="memory",
                data={"period": None, "detail": "month"},
            ),
            dcc.Store(
                id="v7-model-selection",
                storage_type="memory",
                data=initial_model_selection(model_predictions, model_metrics),
            ),
            html.A("Ir al contenido", href="#dashboard-content", className="skip-link"),
            _header(arrivals, months),
            html.Main(
                [
                    _arrivals_panel(arrivals, initial),
                    _seasons_panel(arrivals, occupancy),
                    _models_panel(model_predictions, model_metrics),
                    _data_panel(months),
                ],
                id="dashboard-content",
                tabIndex=-1,
            ),
            html.Footer(
                "Guatemala · Información estadística de INGUAT",
                className="dashboard-footer",
            ),
        ],
        fluid=True,
        className="dashboard-shell",
    )
