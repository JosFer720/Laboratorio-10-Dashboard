from __future__ import annotations

import dash_bootstrap_components as dbc
import pandas as pd
from dash import dcc, html

from tourism_dashboard.exploration import (
    DETAIL_OPTIONS,
    apply_selection,
    make_selection,
    market_labels,
    market_options,
    markets_caption,
    month_options,
    selection_label,
)
from tourism_dashboard.figures import arrivals_figure, markets_figure

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
DROPDOWN_LABELS = {
    "select_all": "Seleccionar todos",
    "deselect_all": "Quitar selección",
    "selected_count": "seleccionados",
    "search": "Buscar",
    "clear_search": "Limpiar búsqueda",
    "clear_selection": "Limpiar selección",
    "no_options_found": "No se encontraron opciones",
}


def _pending_panel(title: str, description: str) -> list:
    return [html.H2(title), html.P(description, className="muted")]


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
                        "Países, regiones agregadas y cruceristas.",
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
    period = f"{arrivals['year'].min()}–{arrivals['year'].max()}"
    return html.Header(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.P("GUATEMALA · INGUAT", className="eyebrow"),
                            html.H1("Observatorio de turismo sostenible"),
                            html.P(
                                f"Llegadas de visitantes no residentes y ocupación hotelera · {period}",
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
                "Fuente: INGUAT, boletines de turismo 2022–2024. Los años y trimestres suman únicamente los meses incluidos en el filtro. Los huecos indican meses sin información.",
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
                "Fuente: INGUAT, boletines de turismo 2022–2024. Los porcentajes son la participación de cada origen en la suma de la selección. Los agregados (Resto de América Central, América del Sur, Europa y Resto del mundo) reúnen varios países y los cruceristas son un grupo aparte, por eso no se comparan como países individuales.",
                className="note chart-source",
            ),
        ],
        className="chart-card",
        **{"aria-describedby": "markets-help"},
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
            html.P(
                "Las cifras son llegadas de visitantes no residentes. Por sí solas no miden la ocupación hotelera ni la presión sobre un destino.",
                className="note page-note",
            ),
        ],
        id="arrivals-panel",
    )


def _data_panel(months: list[dict[str, str]]) -> html.Section:
    return html.Section(
        [
            html.H2("Sobre los datos"),
            html.H3("Qué representan las cifras"),
            html.P(
                "Las llegadas mensuales corresponden a visitantes no residentes en Guatemala. Los orígenes combinan países individuales, regiones agregadas y un segmento de cruceristas. El filtro identifica cada tipo para evitar confundirlos."
            ),
            html.H3("Cobertura y fuente"),
            html.P(
                f"Periodo disponible en esta fuente de llegadas: {months[0]['label']} a {months[-1]['label']}."
            ),
            html.P(
                [
                    "INGUAT, tabla Visitantes no residentes por mes y país de residencia. ",
                    html.A(
                        "Consultar el catálogo de boletines de INGUAT",
                        href="https://biblioteca.inguat.gob.gt/opac/record/8002",
                    ),
                    ".",
                ]
            ),
            html.H3("Límites de interpretación"),
            html.P(
                "El tablero suma las categorías originales sin ajustar las cifras. En febrero, abril y octubre de 2024, esa suma difiere en una unidad del total publicado. No se completan meses ausentes con valores inventados."
            ),
            html.P(
                "La fuente de ocupación hotelera disponible cuenta huéspedes residentes y no residentes. Tiene un alcance distinto al de las llegadas. Una coincidencia entre ambas series no demuestra que una cause la otra ni mide la capacidad de un destino para recibir visitantes."
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


def build_layout(arrivals: pd.DataFrame) -> dbc.Container:
    months = month_options(arrivals)
    initial = make_selection(arrivals, "all", "month")
    return dbc.Container(
        [
            dcc.Store(id="v1-selection", storage_type="memory", data=initial),
            html.A("Ir al contenido", href="#dashboard-content", className="skip-link"),
            _header(arrivals, months),
            html.Main(
                [
                    _arrivals_panel(arrivals, initial),
                    html.Section(
                        _pending_panel(
                            "Temporadas y hospedaje",
                            "La exploración de estacionalidad y ocupación hotelera aún no está disponible en esta vista.",
                        ),
                        id="seasons-panel",
                        hidden=True,
                        className="information-panel",
                    ),
                    html.Section(
                        _pending_panel(
                            "Predicciones y modelos",
                            "Aún no hay resultados de modelos disponibles para consultar. Las cifras de llegadas mostradas en el tablero son observadas.",
                        ),
                        id="models-panel",
                        hidden=True,
                        className="information-panel",
                    ),
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
