from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from tourism_dashboard.application import create_app  # noqa: E402
from tourism_dashboard.config import load_settings  # noqa: E402


settings = load_settings()
app = create_app(
    settings.data_path,
    settings.model_predictions_path,
    settings.model_metrics_path,
)
server = app.server


if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
