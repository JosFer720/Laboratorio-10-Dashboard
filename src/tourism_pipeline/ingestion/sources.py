from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tourism_pipeline.config import PipelineConfig


HASH_CHUNK_BYTES = 1024 * 1024
SHEET_COLUMN = "sheet"


class SourceReadError(RuntimeError):
    """No se pudo leer una fuente: el archivo o una hoja esperada no existe."""


@dataclass(frozen=True)
class FileFingerprint:
    file_name: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class LoadedSource:
    name: str
    data: pd.DataFrame
    fingerprint: FileFingerprint


def fingerprint_file(path: str | Path) -> FileFingerprint:
    path = Path(path)
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(HASH_CHUNK_BYTES), b""):
                digest.update(chunk)
    except OSError as exc:
        raise SourceReadError(f"No se pudo abrir el archivo {path.name}.") from exc
    return FileFingerprint(
        file_name=path.name,
        size_bytes=path.stat().st_size,
        sha256=digest.hexdigest(),
    )


def read_mobility(config: PipelineConfig) -> LoadedSource:
    """Lee las hojas de la movilidad mensual y las une con la columna `sheet`.

    Las tablas se devuelven tal como vienen: sin limpiar ni corregir, para que
    los controles de calidad vean los datos originales.
    """
    path = config.paths.mobility_path
    fingerprint = fingerprint_file(path)
    frames = _read_sheets(path, config.paths.mobility_sheets)
    data = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in frames.items()],
        ignore_index=True,
    )
    return LoadedSource(name="mobility", data=data, fingerprint=fingerprint)


def read_migration(config: PipelineConfig) -> LoadedSource:
    """Lee la hoja de datos de la base de migración tal como viene."""
    path = config.paths.migration_path
    fingerprint = fingerprint_file(path)
    frames = _read_sheets(path, (config.paths.migration_sheet,))
    return LoadedSource(
        name="migration",
        data=frames[config.paths.migration_sheet],
        fingerprint=fingerprint,
    )


def _read_sheets(path: Path, sheets: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    try:
        frames = pd.read_excel(path, sheet_name=list(sheets), engine="openpyxl")
    except ValueError as exc:
        raise SourceReadError(
            f"El archivo {path.name} no tiene todas las hojas esperadas: {', '.join(sheets)}."
        ) from exc
    except OSError as exc:
        raise SourceReadError(f"No se pudo abrir el archivo {path.name}.") from exc
    return frames
