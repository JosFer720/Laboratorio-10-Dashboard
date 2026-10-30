from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from tourism_pipeline.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    expand_months,
    load_config,
)


def test_default_config_loads_with_data_dir_from_environment(tmp_path: Path) -> None:
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})

    assert config.paths.data_dir == tmp_path
    assert config.paths.mobility_path == tmp_path / "BD_moviidad_mensual.xlsx"
    assert config.paths.migration_path == tmp_path / "Base_Migracion_2009-2026jun.xlsx"
    assert len(config.paths.mobility_sheets) == 6
    assert config.paths.results_file == "estimates.csv"
    assert config.paths.reports_path == config.paths.output_dir / "reports"
    assert config.parameters.procedure_version == "1"
    assert config.parameters.migration.traveler_types == ("Turista", "Excursionista")
    assert config.parameters.migration.first_year == 2023
    assert config.parameters.unit == "visitantes únicos del mes"
    assert config.paths.factors_file == "reparto_factors.csv"
    assert config.tracking.experiment_name == "Nivel Nacional"
    assert config.tracking.reproducibility_tolerance == 1e-9


def test_tracking_settings_can_come_from_environment(tmp_path: Path) -> None:
    config = load_config(
        env={
            "INGUAT_DATA_DIR": str(tmp_path),
            "MLFLOW_TRACKING_URI": str(tmp_path / "tracking"),
            "MLFLOW_EXPERIMENT_NAME": "Prueba local",
            "PIPELINE_REPRODUCIBILITY_TOLERANCE": "0.0001",
        }
    )

    assert config.tracking.uri == str(tmp_path / "tracking")
    assert config.tracking.experiment_name == "Prueba local"
    assert config.tracking.reproducibility_tolerance == 0.0001


def test_default_periods_match_observed_coverage(tmp_path: Path) -> None:
    periods = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)}).periods

    assert len(periods.mobility_coverage) == 10
    assert pd.Timestamp("2026-01-01") not in periods.mobility_coverage
    assert pd.Timestamp("2026-02-01") not in periods.mobility_coverage
    assert periods.estimate == (pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01"))
    assert periods.evaluation[0] == pd.Timestamp("2026-03-01")
    assert periods.evaluation[-1] == pd.Timestamp("2026-06-01")
    assert set(periods.evaluation) <= set(periods.fit)


def test_missing_data_dir_is_an_error() -> None:
    with pytest.raises(ConfigError, match="INGUAT_DATA_DIR"):
        load_config(env={})


def test_environment_overrides_output_dir(tmp_path: Path) -> None:
    config = load_config(
        env={"INGUAT_DATA_DIR": str(tmp_path), "PIPELINE_OUTPUT_DIR": str(tmp_path / "salida")}
    )

    assert config.paths.output_dir == tmp_path / "salida"


def test_config_path_can_come_from_environment(tmp_path: Path) -> None:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["parameters"]["seed"] = 99
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump(raw), encoding="utf-8")

    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path), "PIPELINE_CONFIG": str(custom)})

    assert config.parameters.seed == 99


def test_expand_months_is_inclusive_sorted_and_unique() -> None:
    months = expand_months(
        [{"start": "2026-03", "end": "2026-04"}, {"start": "2025-12", "end": "2026-03"}],
        "demo",
    )

    assert months == (
        pd.Timestamp("2025-12-01"),
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-02-01"),
        pd.Timestamp("2026-03-01"),
        pd.Timestamp("2026-04-01"),
    )


@pytest.mark.parametrize(
    "ranges",
    [None, [], [{"start": "2026-05", "end": "2026-01"}], [{"start": "mayo", "end": "junio"}], [{"end": "2026-01"}]],
)
def test_expand_months_rejects_invalid_ranges(ranges: list | None) -> None:
    with pytest.raises(ConfigError):
        expand_months(ranges, "demo")


@pytest.mark.parametrize(
    ("section", "value", "message"),
    [
        ("fit", [{"start": "2026-01", "end": "2026-02"}], "ajuste"),
        ("evaluation", [{"start": "2025-09", "end": "2025-10"}, {"start": "2026-07", "end": "2026-07"}], "evaluación"),
        ("estimate", [{"start": "2026-05", "end": "2026-05"}], "cobertura de movilidad"),
    ],
)
def test_inconsistent_periods_are_rejected(
    tmp_path: Path, section: str, value: list, message: str
) -> None:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["periods"][section] = value
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_config(custom, env={"INGUAT_DATA_DIR": str(tmp_path)})


def test_missing_section_names_the_key(tmp_path: Path) -> None:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    del raw["quality"]
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ConfigError, match="quality"):
        load_config(custom, env={"INGUAT_DATA_DIR": str(tmp_path)})


def test_unreadable_config_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No se pudo leer"):
        load_config(tmp_path / "no-existe.yaml", env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.mark.parametrize(
    ("name", "value"),
    [("max_optional_missing_fraction", -0.1), ("zero_count_warning_fraction", 1.1)],
)
def test_quality_thresholds_must_be_fractions(tmp_path: Path, name: str, value: float) -> None:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["quality"]["thresholds"][name] = value
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ConfigError, match="umbrales de calidad"):
        load_config(custom, env={"INGUAT_DATA_DIR": str(tmp_path)})


def test_acceptance_rule_and_versions_store_come_from_configuration(tmp_path: Path) -> None:
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})

    assert config.acceptance.max_mape == 25.0
    assert config.acceptance.min_evaluated_months == 4
    assert config.publication.versions_dir == Path("output") / "versions"
    assert config.paths.evaluation_file == "evaluation.csv"


def test_versions_store_can_live_outside_the_output_directory(tmp_path: Path) -> None:
    config = load_config(
        env={"INGUAT_DATA_DIR": str(tmp_path), "PIPELINE_VERSIONS_DIR": str(tmp_path / "v")}
    )

    assert config.publication.versions_dir == tmp_path / "v"


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [("max_mape", 0, "max_mape"), ("min_evaluated_months", 9, "min_evaluated_months")],
)
def test_invalid_acceptance_rule_is_rejected(tmp_path: Path, key: str, value, message: str) -> None:
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    raw["acceptance"][key] = value
    custom = tmp_path / "custom.yaml"
    custom.write_text(yaml.safe_dump(raw), encoding="utf-8")

    with pytest.raises(ConfigError, match=message):
        load_config(custom, env={"INGUAT_DATA_DIR": str(tmp_path)})
