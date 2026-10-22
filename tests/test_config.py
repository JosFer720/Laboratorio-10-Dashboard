from __future__ import annotations

from pathlib import Path

import pytest

from tourism_dashboard.config import DEFAULT_DATA_PATH, load_settings


def test_default_data_path_uses_the_migration_series() -> None:
    assert DEFAULT_DATA_PATH == Path("data/arrivals_migration_2009_2026.csv")


def test_load_settings_uses_explicit_environment() -> None:
    settings = load_settings(
        {
            "TOURISM_DATA_PATH": "fixtures/arrivals.csv",
            "DASH_HOST": "0.0.0.0",
            "DASH_PORT": "9000",
            "DASH_DEBUG": "true",
        }
    )

    assert settings.data_path == Path("fixtures/arrivals.csv")
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.debug is True


def test_load_settings_rejects_invalid_port() -> None:
    with pytest.raises(ValueError, match="DASH_PORT"):
        load_settings({"DASH_PORT": "not-a-number"})


def test_load_settings_rejects_invalid_debug_value() -> None:
    with pytest.raises(ValueError, match="DASH_DEBUG"):
        load_settings({"DASH_DEBUG": "sometimes"})
