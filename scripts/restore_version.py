"""Lista las versiones aprobadas o vuelve vigente una anterior."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tourism_pipeline.restore import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
