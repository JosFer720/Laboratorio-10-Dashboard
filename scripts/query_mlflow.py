"""Muestra las ejecuciones registradas en MLflow con sus parámetros y artefactos."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tourism_pipeline.config import load_config  # noqa: E402
from tourism_pipeline.tracking import list_run_records  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    records = list_run_records(load_config(), limit=args.limit)
    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
