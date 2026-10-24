from __future__ import annotations

from pathlib import Path

import pytest

from tourism_dashboard.config import (
    DEFAULT_DATA_PATH,
    DEFAULT_MODEL_METRICS_PATH,
    DEFAULT_MODEL_PREDICTIONS_PATH,
    DEFAULT_OCCUPANCY_PATH,
    load_settings,
)


def test_default_data_path_uses_the_migration_series() -> None:
    assert DEFAULT_DATA_PATH == Path("data/arrivals_migration_2009_2026.csv")
    assert DEFAULT_MODEL_PREDICTIONS_PATH == Path("data/model_predictions_s0.csv")
    assert DEFAULT_MODEL_METRICS_PATH == Path("data/model_metrics_s0.csv")
    assert DEFAULT_OCCUPANCY_PATH == Path("data/hotel_occupancy_inguat_2022_2024.csv")


def test_load_settings_uses_explicit_environment() -> None:
    settings = load_settings(
        {
            "TOURISM_DATA_PATH": "fixtures/arrivals.csv",
            "TOURISM_MODEL_PREDICTIONS_PATH": "fixtures/predictions.csv",
            "TOURISM_MODEL_METRICS_PATH": "fixtures/metrics.csv",
            "TOURISM_OCCUPANCY_PATH": "fixtures/occupancy.csv",
            "DASH_HOST": "0.0.0.0",
            "DASH_PORT": "9000",
            "DASH_DEBUG": "true",
        }
    )

    assert settings.data_path == Path("fixtures/arrivals.csv")
    assert settings.model_predictions_path == Path("fixtures/predictions.csv")
    assert settings.model_metrics_path == Path("fixtures/metrics.csv")
    assert settings.occupancy_path == Path("fixtures/occupancy.csv")
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.debug is True


def test_load_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="DASH_PORT"):
        load_settings({"DASH_PORT": "not-a-number"})


def test_load_settings_rejects_invalid_debug_value() -> None:
    with pytest.raises(ValueError, match="DASH_DEBUG"):
        load_settings({"DASH_DEBUG": "sometimes"})
