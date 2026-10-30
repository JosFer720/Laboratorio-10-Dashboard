"""Ejecuta dos veces el pipeline y comprueba que sus resultados sean equivalentes."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tourism_pipeline.config import load_config  # noqa: E402
from tourism_pipeline.reproducibility import check_reproducibility  # noqa: E402


def main() -> int:
    result = check_reproducibility(load_config())
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.equivalent else 1


if __name__ == "__main__":
    raise SystemExit(main())
