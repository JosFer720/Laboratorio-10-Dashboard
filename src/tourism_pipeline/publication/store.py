from __future__ import annotations

import json
import os
import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CURRENT_FILE = "current.json"
HISTORY_FILE = "history.jsonl"
METADATA_FILE = "metadata.json"
STAGING_PREFIX = ".staging-"


class PublicationError(RuntimeError):
    """No se puede publicar ni restaurar la versión pedida."""


@dataclass(frozen=True)
class PublishedVersion:
    version_id: str
    path: Path
    metadata: dict[str, Any]

    def file(self, name: str) -> Path:
        return self.path / name


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json_atomically(path: Path, content: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _append_history(store: Path, event: Mapping[str, Any]) -> None:
    with (store / HISTORY_FILE).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _load_version(store: Path, version_id: str) -> PublishedVersion | None:
    path = store / version_id
    metadata_path = path / METADATA_FILE
    if not metadata_path.is_file():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return PublishedVersion(version_id=version_id, path=path, metadata=metadata)


def _set_current(store: Path, version_id: str, action: str, **details: Any) -> None:
    previous = current_version(store)
    event = {
        "action": action,
        "version": version_id,
        "previous_version": previous.version_id if previous else None,
        "at": _now(),
        **details,
    }
    # El puntero se reemplaza de una sola vez: quien lo lea ve la versión
    # anterior o la nueva, nunca un archivo a medio escribir.
    _write_json_atomically(store / CURRENT_FILE, {"version": version_id, "updated_at": event["at"]})
    _append_history(store, event)


def publish_version(
    store_dir: str | Path,
    version_id: str,
    files: Mapping[str, Path],
    metadata: Mapping[str, Any],
    documents: Mapping[str, Mapping[str, Any]] | None = None,
) -> PublishedVersion:
    """Guarda una versión aprobada en su propia carpeta y la vuelve vigente.

    Los archivos se copian primero a una carpeta temporal del almacén; solo
    cuando están completos la carpeta se renombra y el puntero cambia.
    """
    if not metadata.get("acceptance", {}).get("approved"):
        raise PublicationError("Solo se publican versiones aprobadas por la regla de aceptación.")
    store = Path(store_dir)
    store.mkdir(parents=True, exist_ok=True)
    target = store / version_id
    if target.exists():
        raise PublicationError(f"La versión {version_id} ya existe en el almacén.")
    staging = store / f"{STAGING_PREFIX}{version_id}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        for path in files.values():
            shutil.copy2(path, staging / Path(path).name)
        for name, content in (documents or {}).items():
            (staging / name).write_text(
                json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        record = {**metadata, "version": version_id, "published_at": _now()}
        (staging / METADATA_FILE).write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(staging, target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    _set_current(store, version_id, "publish")
    return _load_version(store, version_id)


def current_version(store_dir: str | Path) -> PublishedVersion | None:
    """Versión aprobada vigente, o `None` si todavía no hay ninguna."""
    store = Path(store_dir)
    pointer = store / CURRENT_FILE
    if not pointer.is_file():
        return None
    version_id = json.loads(pointer.read_text(encoding="utf-8")).get("version")
    return _load_version(store, version_id) if version_id else None


def list_versions(store_dir: str | Path) -> list[PublishedVersion]:
    """Versiones aprobadas guardadas, de la más antigua a la más reciente."""
    store = Path(store_dir)
    if not store.is_dir():
        return []
    versions = [
        version
        for path in store.iterdir()
        if path.is_dir() and not path.name.startswith(STAGING_PREFIX)
        and (version := _load_version(store, path.name)) is not None
    ]
    # El historial conserva el orden real de publicación, aun dentro del mismo segundo.
    order = {
        event["version"]: index
        for index, event in reversed(list(enumerate(read_history(store))))
        if event.get("action") == "publish"
    }
    return sorted(versions, key=lambda version: order.get(version.version_id, len(order)))


def restore_version(store_dir: str | Path, version_id: str) -> PublishedVersion:
    """Vuelve vigente una versión aprobada anterior y registra la restauración."""
    store = Path(store_dir)
    version = _load_version(store, version_id)
    if version is None:
        raise PublicationError(f"No existe la versión {version_id} en {store}.")
    if not version.metadata.get("acceptance", {}).get("approved"):
        raise PublicationError(f"La versión {version_id} no está aprobada.")
    _set_current(store, version_id, "restore")
    return version


def read_history(store_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(store_dir) / HISTORY_FILE
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
