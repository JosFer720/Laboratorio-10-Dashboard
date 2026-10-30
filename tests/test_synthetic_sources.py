from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tourism_pipeline.synthetic import (
    MOBILITY_MONTHS,
    MOBILITY_STRUCTURE,
    PROBLEMS,
    apply_problem,
    build_migration,
    build_mobility,
    write_synthetic_sources,
)


def test_mobility_has_one_sheet_per_destination_and_real_columns() -> None:
    mobility = build_mobility()

    assert set(mobility) == set(MOBILITY_STRUCTURE)
    for frame in mobility.values():
        assert list(frame.columns) == [
            "destino", "sub_grupo", "anio", "mes", "pais", "es_consecutivo",
            "fecha", "visitantes", "dias_persona", "permanencia_prom",
        ]  # fmt: skip
        assert set(frame["fecha"]) == set(MOBILITY_MONTHS)


def test_mobility_has_no_coverage_in_january_and_february_2026() -> None:
    months = {month for frame in build_mobility().values() for month in frame["fecha"]}

    assert pd.Timestamp("2026-01-01") not in months
    assert pd.Timestamp("2026-02-01") not in months


def test_stay_is_consistent_with_person_days() -> None:
    frame = pd.concat(build_mobility().values())

    np.testing.assert_allclose(
        frame["dias_persona"] / frame["visitantes"], frame["permanencia_prom"]
    )
    assert (frame.loc[frame["es_consecutivo"] == "menor a 1 dia", "permanencia_prom"] == 1).all()


def test_migration_matches_source_layout() -> None:
    migration = build_migration()

    assert list(migration.columns) == [
        "Año", "Mes cod", "Mes", "Vía", "Frontera", "País", "Región", "Región dos",
        "Regiones OMT", "MCEO", "Agrupación Residencia", "Tipo de Viajero", "Viajero",
    ]  # fmt: skip
    assert set(migration["Tipo de Viajero"]) == {"Turista", "Excursionista", "Viajero"}
    assert (migration["Viajero"] > 0).all()


def test_same_seed_gives_same_data_and_other_seed_differs() -> None:
    first = build_mobility(seed=3)["Peten"]
    pd.testing.assert_frame_equal(first, build_mobility(seed=3)["Peten"])
    assert not first["visitantes"].equals(build_mobility(seed=4)["Peten"]["visitantes"])
    pd.testing.assert_frame_equal(build_migration(seed=3), build_migration(seed=3))


def test_problem_does_not_modify_original_tables() -> None:
    mobility, migration = build_mobility(), build_migration()
    before = mobility["Antigua"].copy()

    apply_problem(mobility, migration, "negative_visitors")

    pd.testing.assert_frame_equal(mobility["Antigua"], before)


def test_missing_column_problem_removes_visitors() -> None:
    mobility, _ = apply_problem(build_mobility(), build_migration(), "missing_column")

    assert all("visitantes" not in frame.columns for frame in mobility.values())


def test_duplicate_row_problem_repeats_key_rows() -> None:
    mobility, _ = apply_problem(build_mobility(), build_migration(), "duplicate_row")
    key = ["destino", "sub_grupo", "fecha", "pais", "es_consecutivo"]

    assert mobility["Antigua"].duplicated(key).sum() == 2


def test_zero_denominator_problem_zeroes_one_national_month() -> None:
    _, migration = apply_problem(build_mobility(), build_migration(), "zero_denominator")
    december = migration[(migration["Año"] == 2025) & (migration["Mes cod"] == 12)]

    assert (december["Viajero"] == 0).all()
    assert (migration.drop(december.index)["Viajero"] > 0).all()


def test_value_problems_change_the_expected_cells() -> None:
    negative, _ = apply_problem(build_mobility(), build_migration(), "negative_visitors")
    invalid, _ = apply_problem(build_mobility(), build_migration(), "invalid_date")
    missing, _ = apply_problem(build_mobility(), build_migration(), "missing_values")

    assert (negative["Antigua"]["visitantes"] < 0).sum() == 1
    assert invalid["Antigua"]["fecha"].iloc[0] == "no-es-una-fecha"
    assert missing["Antigua"]["visitantes"].isna().sum() == 5


def test_unknown_problem_is_rejected() -> None:
    with pytest.raises(ValueError, match="desconocido"):
        apply_problem(build_mobility(), build_migration(), "otro")


def test_write_synthetic_sources_creates_both_workbooks(tmp_path: Path) -> None:
    paths = write_synthetic_sources(tmp_path / "datos")

    assert paths["mobility"].is_file()
    assert paths["migration"].is_file()
    sheets = pd.read_excel(paths["mobility"], sheet_name=None)
    assert list(sheets) == list(MOBILITY_STRUCTURE)


@pytest.mark.parametrize("problem", PROBLEMS)
def test_every_problem_can_be_written(tmp_path: Path, problem: str) -> None:
    paths = write_synthetic_sources(tmp_path, problem=problem)

    assert paths["mobility"].is_file()
    assert paths["migration"].is_file()
