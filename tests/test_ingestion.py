from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from tourism_pipeline.config import PipelineConfig, load_config
from tourism_pipeline.ingestion import (
    SHEET_COLUMN,
    SourceReadError,
    fingerprint_file,
    read_migration,
    read_mobility,
)
from tourism_pipeline.synthetic import (
    MOBILITY_STRUCTURE,
    build_migration,
    build_mobility,
    write_synthetic_sources,
)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "datos"
    write_synthetic_sources(directory)
    return directory


@pytest.fixture
def config(data_dir: Path) -> PipelineConfig:
    return load_config(env={"INGUAT_DATA_DIR": str(data_dir)})


def test_mobility_joins_every_sheet_with_a_sheet_column(config: PipelineConfig) -> None:
    source = read_mobility(config)

    assert source.name == "mobility"
    assert set(source.data[SHEET_COLUMN]) == set(MOBILITY_STRUCTURE)
    expected_rows = sum(len(frame) for frame in build_mobility().values())
    assert len(source.data) == expected_rows
    assert set(config.quality.mobility_columns) <= set(source.data.columns)


def test_mobility_is_returned_as_read_without_cleaning(config: PipelineConfig) -> None:
    source = read_mobility(config)
    expected = pd.concat(build_mobility().values(), ignore_index=True)

    pd.testing.assert_series_equal(
        source.data["visitantes"], expected["visitantes"], check_dtype=False
    )
    assert source.data["fecha"].dtype.kind == "M"


def test_migration_is_returned_as_read_without_cleaning(config: PipelineConfig) -> None:
    source = read_migration(config)

    assert source.name == "migration"
    assert list(source.data.columns) == list(config.quality.migration_columns)
    pd.testing.assert_frame_equal(source.data, build_migration(), check_dtype=False)


def test_fingerprint_is_the_sha256_of_the_file_and_hides_the_directory(
    config: PipelineConfig,
) -> None:
    source = read_migration(config)
    path = config.paths.migration_path

    assert source.fingerprint.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert source.fingerprint.size_bytes == path.stat().st_size
    assert source.fingerprint.file_name == path.name
    assert str(path.parent) not in repr(source.fingerprint)


def test_fingerprint_changes_when_the_file_changes(tmp_path: Path) -> None:
    path = tmp_path / "datos.bin"
    path.write_bytes(b"abc")
    first = fingerprint_file(path)
    assert fingerprint_file(path) == first

    path.write_bytes(b"abd")

    assert fingerprint_file(path).sha256 != first.sha256


def test_same_seed_writes_equal_workbook_content(tmp_path: Path) -> None:
    a = write_synthetic_sources(tmp_path / "a", seed=5)
    b = write_synthetic_sources(tmp_path / "b", seed=5)
    c = write_synthetic_sources(tmp_path / "c", seed=6)
    values_a = pd.read_excel(a["migration"])
    values_b = pd.read_excel(b["migration"])
    values_c = pd.read_excel(c["migration"])

    pd.testing.assert_frame_equal(values_a, values_b)
    assert not values_a["Viajero"].equals(values_c["Viajero"])


def test_missing_file_is_a_read_error(tmp_path: Path) -> None:
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})

    with pytest.raises(SourceReadError, match="BD_moviidad_mensual.xlsx"):
        read_mobility(config)


def test_missing_sheet_is_a_read_error(tmp_path: Path) -> None:
    write_synthetic_sources(tmp_path)
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})
    wrong = tmp_path / "otra"
    wrong.mkdir()
    with pd.ExcelWriter(wrong / config.paths.migration_file) as writer:
        build_migration().to_excel(writer, sheet_name="Otra", index=False)
    other = load_config(env={"INGUAT_DATA_DIR": str(wrong)})

    with pytest.raises(SourceReadError, match="hojas esperadas"):
        read_migration(other)


def test_missing_column_reaches_the_controls_instead_of_failing(tmp_path: Path) -> None:
    write_synthetic_sources(tmp_path, problem="missing_column")
    config = load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})

    source = read_mobility(config)

    assert "visitantes" not in source.data.columns
