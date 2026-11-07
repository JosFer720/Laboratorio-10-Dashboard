"""Revisa el PBIR, sus interacciones y su correspondencia con el PBIX.

La revisión es estructural. No sustituye abrir el informe y ejecutar sus
consultas e interacciones en Power BI Desktop.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE = "a52f372"
PAGES = {
    "Inicio": "f4891321a84c9cedcf63",
    "Llegadas y mercados": "7ae7283f2a8b4b668889",
    "Temporadas y hospedaje": "b5c62d7445d4499f4fcc",
    "Predicciones y modelos": "d8d440620cb13a60ca2b",
    "Sobre los datos": "3754b77b37755d5b0c31",
    "Detalle de región": "b88313346c3b9b66bbb9",
}
VISUALS = {
    "V1": ("Llegadas y mercados", "88c8af3689835bd26b02", "lineChart"),
    "V2": ("Llegadas y mercados", "4b19faa7236096e48039", "clusteredBarChart"),
    "V3": ("Temporadas y hospedaje", "v3_estacionalidad", "pivotTable"),
    "V4": ("Llegadas y mercados", "a1179305634011f679ed", "lineChart"),
    "V5": ("Temporadas y hospedaje", "4eca71e6ed45a075d88b", "clusteredColumnChart"),
    "V6": ("Temporadas y hospedaje", "c1cb095e0fa0eae39f3f", "scatterChart"),
    "V7": ("Predicciones y modelos", "v7_observado_estimado", "lineChart"),
    "V8": ("Predicciones y modelos", "v8_error_mensual", "clusteredColumnChart"),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def verify(report_dir: Path = ROOT / "powerbi/observatorio_turismo.Report",
           pbix_path: Path = ROOT / "powerbi/observatorio_turismo.pbix",
           model_path: Path = ROOT / "powerbi/observatorio_turismo.SemanticModel/model.bim",
           check_baseline: bool = True) -> dict:
    definition = report_dir / "definition"
    model = load(model_path)["model"]
    fields = {t["name"]: {c["name"] for c in t["columns"]} for t in model["tables"]}
    measures = {t["name"]: {m["name"] for m in t.get("measures", [])} for t in model["tables"]}
    extensions = load(definition / "reportExtensions.json")
    extension_measures = {e["name"]: {m["name"] for m in e["measures"]} for e in extensions["entities"]}
    for entity in extensions["entities"]:
        require(entity["name"] in fields, "Las medidas de informe apuntan a una tabla inexistente.")
        for measure in entity["measures"]:
            require(not re.search(r"SUM\s*\(\s*Predicciones\[observed\]", measure["expression"], re.I), "El observado se está sumando desde la tabla repetida por modelo.")
    index = load(definition / "pages/pages.json")
    require(set(index["pageOrder"]) == set(PAGES.values()), "Faltan páginas del informe.")
    require(index["activePageName"] == PAGES["Inicio"], "La apertura debe mostrar Inicio.")
    page_visuals, page_meta = {}, {}
    for label, ident in PAGES.items():
        page = load(definition / f"pages/{ident}/page.json")
        require(page["displayName"] == label, f"Página mal identificada: {label}.")
        page_meta[label] = page
        visuals = {}
        for path in (definition / f"pages/{ident}/visuals").glob("*/visual.json"):
            visual = load(path)
            require(visual["name"] == path.parent.name, "El nombre del visual no coincide con su carpeta.")
            p = visual["position"]
            require(p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["width"] <= page["width"] + 0.01
                    and p["y"] + p["height"] <= page["height"] + 0.01, f"Visual fuera del lienzo: {label}/{visual['name']}.")
            visuals[visual["name"]] = visual
            for obj in walk(visual):
                for kind in ["Column", "Measure"]:
                    if kind not in obj:
                        continue
                    item = obj[kind]
                    source = item.get("Expression", {}).get("SourceRef", {})
                    table = source.get("Entity")
                    if not table:
                        continue  # Aliases inside serialized filter predicates.
                    name = item.get("Property")
                    catalog = fields if kind == "Column" else (extension_measures if source.get("Schema") == "extension" else measures)
                    require(name in catalog.get(table, set()), f"Referencia inexistente: {table}[{name}].")
        for rule in page.get("visualInteractions", []):
            require(rule["source"] in visuals and rule["target"] in visuals, "Una interacción apunta a un visual inexistente.")
        for nav in ["inicio", "llegadas", "temporadas", "modelos", "datos"]:
            require(f"nav_{nav}" in visuals, f"Falta navegación en {label}.")
        require("filtros_activos" in visuals and "restablecer" in visuals, f"Falta contexto o restablecimiento en {label}.")
        page_visuals[label] = visuals

    for key, (page, name, kind) in VISUALS.items():
        require(name in page_visuals[page] and page_visuals[page][name]["visual"]["visualType"] == kind, f"Falta {key} o fue reemplazada por otra visualización.")
    for page, source, target in [
        ("Llegadas y mercados", VISUALS["V1"][1], VISUALS["V2"][1]),
        ("Temporadas y hospedaje", VISUALS["V3"][1], VISUALS["V5"][1]),
        ("Predicciones y modelos", VISUALS["V7"][1], VISUALS["V8"][1]),
    ]:
        require(any(r["source"] == source and r["target"] == target and r["type"] in {"DataFilter", "HighlightFilter"}
                    for r in page_meta[page].get("visualInteractions", [])), "Falta un enlace requerido entre gráficos.")
    prediction_rules = page_meta["Predicciones y modelos"]["visualInteractions"]
    for target in ["v8_error_mensual", "tabla_metricas"]:
        require(any(r == {"source": "filtro_modelo", "target": target, "type": "NoFilter"} for r in prediction_rules), "La comparación de los tres modelos recibe el filtro de V7.")
    for page in ["Llegadas y mercados", "Temporadas y hospedaje", "Predicciones y modelos"]:
        for name, group in [("filtro_anio", "PeriodoAnio"), ("filtro_mes", "PeriodoMes")]:
            require(page_visuals[page][name]["visual"]["syncGroup"]["groupName"] == group, "Los períodos no están sincronizados.")
    detail = page_meta["Detalle de región"]
    require(detail.get("type") == "Drillthrough" and detail.get("visibility") == "HiddenInViewMode", "El detalle no está configurado como drillthrough oculto.")
    require(detail["pageBinding"]["parameters"][0]["fieldExpr"]["Column"]["Property"] == "origin_region", "El detalle no recibe la región.")
    require("volver" in page_visuals["Detalle de región"], "Falta el regreso del detalle.")
    bookmarks = load(definition / "bookmarks/bookmarks.json")["items"]
    for entry in bookmarks:
        bookmark = load(definition / f"bookmarks/{entry['name']}.bookmark.json")
        require(not bookmark["options"]["suppressData"], "El marcador no restaura filtros.")
        require(set(bookmark["explorationState"]["sections"]) == set(PAGES.values()), "El marcador no contempla todas las páginas sincronizadas.")
        for ident, section in bookmark["explorationState"]["sections"].items():
            label = next(label for label, page_id in PAGES.items() if page_id == ident)
            require(set(section["visualContainers"]) == set(page_visuals[label]), "El marcador omite selecciones de algunos visuales.")
    require(len(bookmarks) == 6, "Falta un marcador de restablecimiento por página.")

    collisions = []
    for label, visuals in page_visuals.items():
        rows = list(visuals.values())
        for i, first in enumerate(rows):
            a = first["position"]
            for second in rows[i + 1:]:
                b = second["position"]
                dx = min(a["x"] + a["width"], b["x"] + b["width"]) - max(a["x"], b["x"])
                dy = min(a["y"] + a["height"], b["y"] + b["height"]) - max(a["y"], b["y"])
                if dx > 1 and dy > 1:
                    collisions.append(f"{label}: {first['name']} / {second['name']}")
    require(not collisions, "Hay objetos superpuestos: " + "; ".join(collisions))

    with zipfile.ZipFile(pbix_path) as pbix:
        require(pbix.testzip() is None, "El PBIX tiene errores de integridad ZIP.")
        imported = pbix.read("DataModel")
        source_names = set()
        for folder in ["definition", "StaticResources"]:
            for path in (report_dir / folder).rglob("*"):
                if path.is_file():
                    name = "Report/" + path.relative_to(report_dir).as_posix()
                    source_names.add(name)
                    require(pbix.read(name) == path.read_bytes(), f"El PBIX no contiene la última versión de {name}.")
        embedded = {n for n in pbix.namelist() if n.startswith(("Report/definition/", "Report/StaticResources/"))}
        require(source_names == embedded, "Hay contenido de informe desactualizado en el PBIX.")
    if check_baseline:
        content = subprocess.run(["git", "show", f"{BASELINE}:powerbi/observatorio_turismo.pbix"], cwd=ROOT,
                                 check=True, capture_output=True).stdout
        with zipfile.ZipFile(io.BytesIO(content)) as baseline:
            require(imported == baseline.read("DataModel"), "Cambió el modelo importado respecto de la versión recibida.")
    return {
        "alcance": "Revisión estructural; ejecución y revisión visual en Power BI Desktop no realizadas en esta sesión.",
        "paginas": len(PAGES), "visualizaciones_principales": len(VISUALS),
        "marcadores": len(bookmarks), "medidas_de_informe": sum(len(e["measures"]) for e in extensions["entities"]),
        "referencias_validas": True, "objetos_superpuestos": len(collisions),
        "pbir_y_pbix_coinciden": True,
        "modelo_importado_conservado": check_baseline,
        "sha256_modelo": hashlib.sha256(imported).hexdigest(),
        "sha256_pbix": hashlib.sha256(pbix_path.read_bytes()).hexdigest(),
        "bytes_pbix": pbix_path.stat().st_size,
        "graficos": {v: {"pagina": p, "nombre": n, "tipo": t} for v, (p, n, t) in VISUALS.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Revisión detenida: {exc}\n")
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content, encoding="utf-8")
    print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
