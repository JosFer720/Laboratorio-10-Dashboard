"""Ejecuta las tres tareas y controles de Dash sobre sus callbacks HTTP reales.

Requiere iniciar la referencia lab10-final. No simula clics del navegador ni
atribuye tiempos HTTP a una persona. Guarda las figuras recibidas del servidor.
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


class DashClient:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.state = {}
        self.calls = []
        self.figures = {}
        self.dependencies = self.get("/_dash-dependencies")
        self.layout = self.get("/_dash-layout")
        self.collect(self.layout)

    def get(self, path):
        with urllib.request.urlopen(self.url + path, timeout=30) as response:
            return json.load(response)

    def collect(self, item):
        if isinstance(item, dict):
            props = item.get("props", {})
            if "id" in props:
                for key, value in props.items():
                    self.state[(props["id"], key)] = value
            for value in item.values():
                self.collect(value)
        elif isinstance(item, list):
            for value in item:
                self.collect(value)

    def call(self, target, changed=None, **overrides):
        for key, value in overrides.items():
            component, prop = key.rsplit("__", 1)
            self.state[(component.replace("_", "-"), prop)] = value
        dep = next(d for d in self.dependencies if target in d["output"].strip(".").split("..."))
        identifiers = dep["output"].strip(".").split("...")
        outputs = [{"id": item.rsplit(".", 1)[0], "property": item.rsplit(".", 1)[1]} for item in identifiers]
        payload = {"output": dep["output"], "outputs": outputs if dep["output"].startswith("..") else outputs[0],
                   "inputs": [dict(item, value=self.state.get((item["id"], item["property"]))) for item in dep["inputs"]],
                   "state": [], "changedPropIds": [changed or dep["inputs"][0]["id"] + "." + dep["inputs"][0]["property"]]}
        request = urllib.request.Request(self.url + "/_dash-update-component", data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
        start = time.perf_counter()
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)["response"]
        elapsed = (time.perf_counter() - start) * 1000
        self.calls.append({"salida": target, "milisegundos_http": round(elapsed, 3)})
        for component, props in result.items():
            for key, value in props.items():
                self.state[(component, key)] = value
                if key == "figure":
                    self.figures[component] = value
        return result


def check(condition, message):
    if not condition:
        raise ValueError(message)


def run(url: str, output: Path):
    client = DashClient(url)
    tasks = []
    start = time.perf_counter()
    client.state[("period-start", "value")] = "2025-01-01"
    client.state[("period-end", "value")] = "2025-12-01"
    client.state[("origin-filter", "value")] = "all"
    client.call("arrivals-timeline.figure", "period-end.value")
    peak = client.state[("peak-arrivals", "children")]
    month = client.state[("peak-month", "children")]
    check(peak == "365.573" and "2025" in month and "iciembre" in month, "No coincide el máximo de 2025.")
    tasks.append({"prueba": 1, "resultado": {"mes": month, "llegadas_mostradas": peak,
                  "total_2025_mostrado": client.state[("arrivals-total", "children")]},
                  "coincide": True, "milisegundos_http_tarea": round((time.perf_counter() - start) * 1000, 3)})
    client.figures["prueba1_llegadas_2025"] = client.figures["arrivals-timeline"]

    start = time.perf_counter()
    client.state[("time-detail", "value")] = "year"
    client.call("market-share-chart.figure", "time-detail.value")
    traces = [trace for trace in client.figures["market-share-chart"]["data"] if trace.get("customdata")]
    regions = {trace["name"]: trace["customdata"][0] for trace in traces}
    check(len(regions) == 5, "No se mostraron cinco regiones.")
    central = regions["América Central"]
    client.call("origin-filter.value", "market-share-chart.clickData", market_share_chart__clickData={"points": [{"customdata": central}]})
    check(client.state[("origin-filter", "value")] == "region:América Central", "No se activó el detalle de región.")
    client.state[("time-detail", "value")] = "month"
    client.call("v1-selection.data", "origin-filter.value")
    client.call("market-chart.figure", "v1-selection.data")
    bars = client.figures["market-chart"]["data"][0]
    best = bars["y"][0]
    best_count = bars["x"][0]
    best_share = bars["customdata"][0][1]
    check(best == "El Salvador" and round(best_count) == 1582845 and best_share == "73,8", "No coincide El Salvador dentro de América Central.")
    client.figures["prueba2_paises_region_2025"] = client.figures["market-chart"]
    client.call("origin-filter.value", "market-share-back.n_clicks", market_share_back__n_clicks=1)
    client.call("market-share-chart.figure", "origin-filter.value")
    regions_after = [t for t in client.figures["market-share-chart"]["data"] if t.get("customdata")]
    check(client.state[("origin-filter", "value")] == "all" and len(regions_after) == 5, "No se regresó a las cinco regiones.")
    tasks.append({"prueba": 2, "resultado": {"region": "América Central", "llegadas_region_mostradas": central[2],
                  "participacion_region_porcentaje": central[3], "pais": best, "llegadas_pais": best_count,
                  "participacion_pais_porcentaje": best_share, "regiones_al_regresar": len(regions_after)},
                  "coincide": True, "milisegundos_http_tarea": round((time.perf_counter() - start) * 1000, 3)})

    start = time.perf_counter()
    client.call("arrivals-panel.hidden", "main-tabs.active_tab", main_tabs__active_tab="models")
    models = []
    for model_id in ["lstm-catch22-contexto-w24", "prophet", "arima-1-1-1"]:
        client.call("v7-model-selection.data", "model-selector.value", model_selector__value=model_id)
        client.call("model-evaluation-chart.figure", "v7-model-selection.data")
        client.call("model-errors-chart.figure", "v7-model-selection.data")
        errors = client.figures["model-errors-chart"]["data"][0]
        i = next(i for i, item in enumerate(errors["customdata"]) if "iciembre" in item[0] and "2025" in item[0])
        models.append({"model_id": model_id, "mape_mostrado": client.state[("model-mape", "children")],
                       "observado_diciembre_2025": errors["customdata"][i][1], "error_diciembre_2025": errors["y"][i]})
        if model_id == "lstm-catch22-contexto-w24":
            client.figures["prueba3_observado_estimado"] = client.figures["model-evaluation-chart"]
            client.figures["prueba3_error_lstm"] = client.figures["model-errors-chart"]
    check(all(abs(row["observado_diciembre_2025"] - 365573.0218067979) < 1e-6 for row in models), "El observado cambió entre modelos.")
    check(round(models[0]["error_diciembre_2025"]) == -142131, "El error de LSTM no coincide.")
    tasks.append({"prueba": 3, "resultado": {"mejor_modelo": models[0]["model_id"], "modelos": models},
                  "coincide": True, "milisegundos_http_tarea": round((time.perf_counter() - start) * 1000, 3)})

    # Exercise all eight figures and a real no-data response from the server.
    client.state[("period-start", "value")] = "2022-01-01"
    client.state[("period-end", "value")] = "2024-12-01"
    client.call("seasonality-chart.figure", "period-end.value")
    client.call("occupancy-chart.figure", "period-end.value")
    client.call("arrivals-occupancy-chart.figure", "period-end.value")
    client.call("occupancy-chart.figure", "period-end.value", period_start__value="2025-01-01", period_end__value="2025-12-01")
    no_data = client.figures["occupancy-chart"]["layout"].get("annotations", [])
    check(any("No hay" in a.get("text", "") for a in no_data), "No apareció el mensaje sin ocupación.")
    client.call("arrivals-panel.hidden", "main-tabs.active_tab", main_tabs__active_tab="arrivals")
    # A second consistency indicator through the displayed Dash summary.
    client.call("arrivals-timeline.figure", "period-end.value", period_start__value="2024-01-01", period_end__value="2024-12-01")
    total_2024 = client.state[("arrivals-total", "children")]
    check(total_2024 == "3.274.436", "El total mostrado de 2024 no coincide.")
    for _ in range(8):
        client.call("arrivals-timeline.figure", "period-end.value")
    durations = [item["milisegundos_http"] for item in client.calls if item["salida"] == "arrivals-timeline.figure"][-8:]
    output.mkdir(parents=True, exist_ok=True)
    for name, figure in client.figures.items():
        if name.startswith("prueba"):
            (output / f"{name}.plotly.json").write_text(json.dumps(figure, ensure_ascii=False), encoding="utf-8", newline="\n")
    result = {
        "fecha_local": datetime.now(ZoneInfo("America/Guatemala")).isoformat(),
        "metodo": "Callbacks HTTP reales del servidor Dash lab10-final; no son clics ni cronometraje de uso humano.",
        "plataforma": platform.platform(), "referencia": "29a091d", "pruebas": tasks,
        "indicador_llegadas_2024_mostrado": total_2024, "mensaje_sin_hospedaje": True,
        "rendimiento_http": {"muestras": len(durations), "mediana_ms": statistics.median(durations), "minimo_ms": min(durations), "maximo_ms": max(durations)},
        "llamadas_http": client.calls,
        "alcance": "Control adicional del servidor de Dash; los clics y tiempos de uso se registran en resultados_pruebas.md.",
    }
    (output / "pruebas_http.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8051")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/lab12/evidencia_http")
    args = parser.parse_args()
    result = run(args.url, args.output)
    print(json.dumps({"pruebas_aprobadas": len(result["pruebas"]), "rendimiento_http": result["rendimiento_http"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
