from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DATA_PATH = Path("data/arrivals_inguat_2022_2024.csv")
TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"", "0", "false", "no", "off"}


@dataclass(frozen=True)
class Settings:
    data_path: Path
    host: str
    port: int
    debug: bool


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env
    port_value = values.get("DASH_PORT", "8050")
    debug_value = values.get("DASH_DEBUG", "false").strip().lower()

    try:
        port = int(port_value)
    except ValueError as exc:
        raise ValueError("DASH_PORT debe ser un numero entero.") from exc
    if not 1 <= port <= 65_535:
        raise ValueError("DASH_PORT debe estar entre 1 y 65535.")

    if debug_value in TRUE_VALUES:
        debug = True
    elif debug_value in FALSE_VALUES:
        debug = False
    else:
        raise ValueError("DASH_DEBUG debe ser true o false.")

    return Settings(
        data_path=Path(values.get("TOURISM_DATA_PATH", DEFAULT_DATA_PATH)),
        host=values.get("DASH_HOST", "127.0.0.1"),
        port=port,
        debug=debug,
    )
