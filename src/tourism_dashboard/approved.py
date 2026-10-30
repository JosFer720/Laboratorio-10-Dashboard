"""Consulta de instantáneas aprobadas, sin ejecutar etapas del pipeline."""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, dcc, html

from tourism_dashboard.figures import OBSERVED, ESTIMATED
from tourism_pipeline.publication import current_version


UNAVAILABLE = "Estimaciones no disponibles: no hay una versión aprobada vigente que se pueda consultar."
LIMITS = (
    "Son estimaciones de visitantes únicos por subdestino; no se suman entre lugares ni meses. "
    "Se dispone de pocos meses para evaluar y las fuentes miden poblaciones distintas. "
    "No hay observaciones comparables para enero y febrero de 2026: su error se desconoce. "
    "La validación histórica no garantiza la precisión de esos dos meses ni permite atribuir causas."
)


def versions_path():
    return Path(os.environ.get("PIPELINE_VERSIONS_DIR") or Path(os.environ.get("PIPELINE_OUTPUT_DIR", "output")) / "versions")


def read_approved(store):
    version = current_version(store)
    if version is None or not version.metadata.get("acceptance", {}).get("approved"):
        return None
    config = json.loads(version.file("effective_config.json").read_text(encoding="utf-8"))
    estimates = pd.read_csv(version.file(config["paths"]["results_file"]))
    observed_path = version.file("observed.csv")
    observed = pd.read_csv(observed_path) if observed_path.is_file() else pd.DataFrame(columns=["destination", "period", "visitors"])
    required = {"destination", "period", "value", "kind", "run_id", "unit", "generated_at", "procedure_version"}
    if estimates.empty or not required <= set(estimates.columns):
        raise ValueError("La versión no contiene estimaciones completas.")
    if not estimates["kind"].eq("estimate").all() or not estimates["run_id"].eq(version.metadata["run_id"]).all():
        raise ValueError("Las estimaciones no corresponden a la versión vigente.")
    values = estimates["value"].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any() or estimates.duplicated(["destination", "period"]).any():
        raise ValueError("Las estimaciones no son válidas.")
    for table in (estimates, observed):
        table["period"] = pd.to_datetime(table["period"], errors="raise")
    return version, estimates, observed


def approved_figure(estimates, observed, destination):
    figure = go.Figure()
    rows = observed.loc[observed["destination"].eq(destination)].sort_values("period")
    estimates = estimates.loc[estimates["destination"].eq(destination)].sort_values("period")
    dates = pd.concat([rows["period"], estimates["period"]])
    if not dates.empty:
        months = pd.date_range(dates.min(), dates.max(), freq="MS")
        values = rows.set_index("period")["visitors"].reindex(months)
        figure.add_trace(go.Scatter(x=months, y=values, name="Observado", mode="lines+markers",
                                   connectgaps=False, line={"color": OBSERVED}))
        figure.add_trace(go.Scatter(x=estimates["period"], y=estimates["value"], name="Estimado",
                                   mode="lines+markers", line={"color": ESTIMATED, "dash": "dash"}))
    figure.update_layout(template="plotly_white", yaxis_title="Visitantes únicos del mes", xaxis_title="Mes",
                         legend={"orientation": "h"}, margin={"l": 55, "r": 20, "t": 20, "b": 45})
    return figure


def render_approved(store, destination=None):
    try:
        snapshot = read_approved(store)
        if snapshot is None:
            return [html.P(UNAVAILABLE, role="status")], []
        version, estimates, observed = snapshot
        destinations = sorted(estimates["destination"].unique())
        destination = destination if destination in destinations else destinations[0]
        validation = version.metadata["validation"]
        selected = estimates.loc[estimates["destination"].eq(destination)]
        rows = observed.loc[observed["destination"].eq(destination)]
        children = [
            html.P(f"Actualización: {version.metadata['generated_at']} · {destination}"),
            html.P(f"MAPE: {validation['mape']:.1f} %. Error porcentual absoluto promedio al ocultar meses observados. "
                   f"Meses evaluados: {', '.join(validation['evaluated_periods'])}. Los observados iguales a cero se excluyen de este porcentaje."),
            html.P(LIMITS, className="note"),
            html.P("Observado: azul continuo. Estimado: naranja discontinuo. Un mes sin observación queda sin dato, nunca en cero."),
            dcc.Graph(figure=approved_figure(estimates, observed, destination), config={"displaylogo": False}),
            html.Table([
                html.Thead(html.Tr([html.Th("Mes"), html.Th("Observado"), html.Th("Estimado · visitantes únicos")])),
                html.Tbody([html.Tr([
                    html.Td(f"{row.period:%Y-%m}"),
                    html.Td("Sin dato" if rows.loc[rows["period"].eq(row.period)].empty else f"{rows.loc[rows['period'].eq(row.period), 'visitors'].iloc[0]:,.0f}"),
                    html.Td(f"{row.value:,.0f}"),
                ]) for row in selected.itertuples()]),
            ]),
        ]
        return children, [{"label": name, "value": name} for name in destinations]
    except (OSError, ValueError, KeyError, TypeError):
        return [html.P(UNAVAILABLE, role="status")], []


def approved_panel():
    return html.Section([
        html.H2("Visitantes por subdestino · versión aprobada"),
        html.Label("Subdestino", htmlFor="approved-destination"),
        dcc.Dropdown(id="approved-destination", options=[], placeholder="Selecciona un subdestino", clearable=False),
        html.Div(id="approved-content", **{"aria-live": "polite"}),
        dcc.Interval(id="approved-refresh", interval=30_000),
    ], className="information-panel", id="approved-panel")


def register_approved_callbacks(app, store):
    @app.callback(Output("approved-content", "children"), Output("approved-destination", "options"),
                  Input("approved-refresh", "n_intervals"), Input("approved-destination", "value"))
    def update_approved(_ticks, destination):
        return render_approved(store, destination)
