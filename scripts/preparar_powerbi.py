"""Crea una copia local del proyecto con la carpeta de datos ya configurada.

No sobrescribe proyectos existentes ni modifica las rutas de la versión en Git.
Ejecutar con Python desde Windows antes de abrir el proyecto en Power BI Desktop.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from verificar_powerbi import FILES, ROOT, verify


def prepare(data_dir: Path, output_dir: Path) -> Path:
    data_dir, output_dir = data_dir.resolve(), output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"La carpeta {output_dir} ya existe. Usa --output con otra carpeta para conservar sus cambios.")
    verify(data_dir)
    for name in FILES:
        if not (data_dir / name).is_file():
            raise FileNotFoundError(data_dir / name)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    source = ROOT / "powerbi"
    with tempfile.TemporaryDirectory(prefix=".powerbi-", dir=output_dir.parent) as temporary:
        staging = Path(temporary) / "proyecto"
        staging.mkdir()
        for name in ("observatorio_turismo.Report", "observatorio_turismo.SemanticModel"):
            shutil.copytree(source / name, staging / name, ignore=shutil.ignore_patterns(".pbi"))
        for name in ("observatorio_turismo.pbip", "tema_observatorio.json"):
            shutil.copy2(source / name, staging / name)
        model_path = staging / "observatorio_turismo.SemanticModel/model.bim"
        database = json.loads(model_path.read_text(encoding="utf-8"))
        parameter = next(e for e in database["model"]["expressions"] if e["name"] == "pCarpetaDatos")
        literal = '"' + data_dir.as_posix().replace('"', '""') + '"'
        parameter["expression"] = [literal + ' meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]']
        model_path.write_text(json.dumps(database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(output_dir)
    return output_dir / "observatorio_turismo.pbip"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output", type=Path, default=ROOT / "powerbi/local")
    args = parser.parse_args()
    try:
        project = prepare(args.data_dir, args.output)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Preparación detenida: {exc}\n")
    print(f"Proyecto preparado: {project}")
    print("Ábrelo en Power BI Desktop, actualiza y guarda como powerbi/observatorio_turismo.pbix.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
