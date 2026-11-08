"""Mide el arranque y la respuesta del tablero Dash de referencia (lab10-final).

Inicia la aplicación de la carpeta indicada, mide cuánto tarda en servir la
página y su layout, y mide los callbacks que se ejecutan al aplicar el filtro
de 2025 y al cambiar a la pestaña de predicciones. Repite cada medición y
guarda el resultado en JSON.

Uso:
    python scripts/medir_rendimiento_dash.py --app C:/Lab12/tablero-lab10 --python C:/Lab12/venv_lab10/Scripts/python.exe
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from pruebas_http_lab12 import DashClient  # noqa: E402


def wait_ready(url: str, timeout: float = 120.0) -> None:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        try:
            with urllib.request.urlopen(url + "/", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            time.sleep(0.05)
    raise TimeoutError("El tablero no respondió a tiempo.")


def summary(values: list[float]) -> dict:
    return {"muestras_ms": [round(v, 1) for v in values], "mediana_ms": round(statistics.median(values), 1),
            "minimo_ms": round(min(values), 1), "maximo_ms": round(max(values), 1)}


def measure(app_dir: Path, python: Path, port: int, starts: int, repeats: int) -> dict:
    url = f"http://127.0.0.1:{port}"
    env = {**__import__("os").environ, "DASH_PORT": str(port), "DASH_DEBUG": "false"}
    startup, layout_ready = [], []
    filter_ms, tab_ms = [], []
    for i in range(starts):
        begin = time.perf_counter()
        process = subprocess.Popen([str(python), "app.py"], cwd=app_dir, env=env,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            wait_ready(url)
            startup.append((time.perf_counter() - begin) * 1000)
            client = DashClient(url)  # descarga dependencias y layout, como hace el navegador al cargar
            layout_ready.append((time.perf_counter() - begin) * 1000)
            if i == starts - 1:
                for _ in range(repeats):
                    client.state[("period-start", "value")] = "2025-01-01"
                    client.state[("period-end", "value")] = "2025-12-01"
                    client.state[("origin-filter", "value")] = "all"
                    t = time.perf_counter()
                    client.call("arrivals-timeline.figure", "period-end.value")
                    client.call("market-chart.figure", "v1-selection.data")
                    filter_ms.append((time.perf_counter() - t) * 1000)
                    t = time.perf_counter()
                    client.call("arrivals-panel.hidden", "main-tabs.active_tab", main_tabs__active_tab="models")
                    client.call("model-evaluation-chart.figure", "v7-model-selection.data")
                    client.call("model-errors-chart.figure", "v7-model-selection.data")
                    tab_ms.append((time.perf_counter() - t) * 1000)
                    client.call("arrivals-panel.hidden", "main-tabs.active_tab", main_tabs__active_tab="arrivals")
        finally:
            process.terminate()
            process.wait(timeout=30)
        time.sleep(2)
    return {
        "fecha_local": datetime.now(ZoneInfo("America/Guatemala")).isoformat(timespec="seconds"),
        "referencia": "lab10-final (29a091d)",
        "plataforma": platform.platform(),
        "python": platform.python_version(),
        "metodo": ("Arranque: desde lanzar python app.py hasta que la página responde y hasta que se sirven "
                   "las dependencias y el layout de Dash. Filtro: callbacks de la serie temporal y de mercados "
                   "con enero a diciembre de 2025. Cambio de pestaña: callbacks que muestran Predicciones y "
                   "modelos y dibujan V7 y V8. Tiempos de solicitud HTTP al servidor local; no incluyen el "
                   "dibujo de las figuras en el navegador."),
        "arranque_hasta_responder": summary(startup),
        "arranque_hasta_layout": summary(layout_ready),
        "respuesta_filtro_2025": summary(filter_ms),
        "cambio_a_predicciones": summary(tab_ms),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--app", type=Path, required=True, help="Carpeta del tablero lab10-final.")
    parser.add_argument("--python", type=Path, default=Path(sys.executable), help="Intérprete con las dependencias del tablero.")
    parser.add_argument("--port", type=int, default=8052)
    parser.add_argument("--arranques", type=int, default=3)
    parser.add_argument("--repeticiones", type=int, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/lab12/rendimiento_dash.json")
    args = parser.parse_args()
    result = measure(args.app, args.python, args.port, args.arranques, args.repeticiones)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content, encoding="utf-8", newline="\n")
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
