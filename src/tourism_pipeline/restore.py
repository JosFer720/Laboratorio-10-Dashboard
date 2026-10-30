from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence

from tourism_pipeline.config import ConfigError, load_config
from tourism_pipeline.publication import (
    PublicationError,
    current_version,
    list_versions,
    read_history,
    restore_version,
)
from tourism_pipeline.tracking import record_restoration


EXIT_OK = 0
EXIT_ERROR = 1


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="restore_version",
        description="Lista las versiones aprobadas o vuelve vigente una anterior.",
    )
    parser.add_argument("--version", help="Identificador de la versión que se vuelve vigente.")
    parser.add_argument("--config", default=None, help="Archivo de configuración.")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        config = load_config(args.config, env=env)
    except ConfigError as exc:
        print(f"Configuración inválida: {exc}")
        return EXIT_ERROR
    store = config.publication.versions_dir

    if args.version:
        try:
            version = restore_version(store, args.version)
        except PublicationError as exc:
            print(f"No se restauró ninguna versión: {exc}")
            return EXIT_ERROR
        restored_at = read_history(store)[-1]["at"]
        tracking_run_id = version.metadata.get("tracking_run_id")
        if tracking_run_id:
            record_restoration(config, tracking_run_id, restored_at)
        print(f"Versión vigente restaurada: {version.version_id} ({restored_at})")
        return EXIT_OK

    current = current_version(store)
    versions = list_versions(store)
    if not versions:
        print(f"No hay versiones aprobadas en {store}.")
        return EXIT_OK
    print(f"Versiones aprobadas en {store}:")
    for version in versions:
        marker = "*" if current and version.version_id == current.version_id else " "
        validation = version.metadata.get("validation", {})
        print(
            f" {marker} {version.version_id}  publicada {version.metadata.get('published_at')}"
            f"  MAPE {validation.get('mape', float('nan')):.1f} %"
        )
    print("* versión vigente")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
