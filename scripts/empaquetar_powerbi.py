"""Incorpora el informe PBIR al PBIX existente sin modificar su modelo importado.

El resultado requiere abrirse y guardarse en Power BI Desktop para comprobar
su ejecución. Conserva datos y metadatos del modelo; no ejecuta M ni DAX.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def package(input_path: Path, report_dir: Path, output_path: Path) -> dict:
    replacement = {}
    for folder in ("definition", "StaticResources"):
        for path in sorted((report_dir / folder).rglob("*")):
            if path.is_file():
                replacement["Report/" + path.relative_to(report_dir).as_posix()] = path.read_bytes()
    if "Report/definition/report.json" not in replacement:
        raise ValueError("No se encontró la definición del informe.")
    with zipfile.ZipFile(input_path) as source:
        if source.testzip() is not None:
            raise ValueError("El contenedor de entrada tiene un error de integridad.")
        original_model = source.read("DataModel")
        remaining = [(info, source.read(info.filename)) for info in source.infolist()
                     if not info.filename.startswith(("Report/definition/", "Report/StaticResources/"))
                     and info.filename != "SecurityBindings"]

    # A changed report invalidates its saved Desktop bindings. Desktop recreates
    # this entry when saving. Its stale content must not accompany a new report.
    namespace = "http://schemas.openxmlformats.org/package/2006/content-types"
    ET.register_namespace("", namespace)
    updated = []
    for info, data in remaining:
        if info.filename == "[Content_Types].xml":
            types = ET.fromstring(data)
            for child in list(types):
                if child.attrib.get("PartName") == "/SecurityBindings":
                    types.remove(child)
            data = ET.tostring(types, encoding="utf-8", xml_declaration=True)
        updated.append((info, data))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=".informe-", suffix=".pbix", dir=output_path.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as target:
            for info, data in updated:
                target.writestr(info, data)
            for name, data in replacement.items():
                target.writestr(name, data)
        with zipfile.ZipFile(temporary) as result:
            if result.testzip() is not None or result.read("DataModel") != original_model:
                raise ValueError("El contenedor generado no conserva el modelo original.")
        os.replace(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
    return {"archivos_informe": len(replacement), "sha256_modelo_conservado": hashlib.sha256(original_model).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "powerbi/observatorio_turismo.pbix")
    parser.add_argument("--report", type=Path, default=ROOT / "powerbi/observatorio_turismo.Report")
    parser.add_argument("--output", type=Path, default=ROOT / "powerbi/observatorio_turismo.pbix")
    args = parser.parse_args()
    result = package(args.input, args.report, args.output)
    print(f"PBIX actualizado: {args.output}")
    print(f"Modelo conservado: {result['sha256_modelo_conservado']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
