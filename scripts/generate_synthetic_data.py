"""Genera fuentes sintéticas con la estructura de las reales para probar el pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tourism_pipeline.synthetic import PROBLEMS, write_synthetic_sources  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Carpeta donde se escriben los archivos.")
    parser.add_argument(
        "--problem",
        choices=PROBLEMS,
        default=None,
        help="Introduce un problema conocido para probar la detección.",
    )
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    paths = write_synthetic_sources(args.directory, problem=args.problem, seed=args.seed)
    for path in paths.values():
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
