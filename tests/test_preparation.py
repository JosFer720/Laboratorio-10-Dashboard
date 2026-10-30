from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.preparation import (
    RepartoError,
    VISITOR_COLUMNS,
    coverage_table,
    national_entries,
    prepare,
    reparto_factors,
    subdestination_visitors,
)
from tourism_pipeline.synthetic import MOBILITY_STRUCTURE, build_migration, build_mobility


@pytest.fixture
def config(tmp_path: Path):
    return load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.fixture
def mobility() -> pd.DataFrame:
    return pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in build_mobility().items()],
        ignore_index=True,
    )


@pytest.fixture
def migration() -> pd.DataFrame:
    return build_migration()


def test_national_entries_sum_only_configured_traveler_types(config, migration):
    entries = national_entries(migration, config).set_index("period")["entries"]

    december = migration.loc[(migration["Año"] == 2025) & (migration["Mes cod"] == 12)]
    expected = december.loc[
        december["Tipo de Viajero"].isin(["Turista", "Excursionista"]), "Viajero"
    ].sum()
    assert entries[pd.Timestamp("2025-12-01")] == pytest.approx(expected)
    assert len(entries) == 42


def test_national_entries_skip_years_before_the_methodological_break(config, migration):
    older = migration.iloc[:4].assign(**{"Año": 2022})
    entries = national_entries(pd.concat([older, migration]), config)

    assert entries["period"].min() == pd.Timestamp("2023-01-01")


def test_visitors_are_one_row_per_subdestination_and_month(mobility):
    visitors = subdestination_visitors(mobility)
    subdestinations = sum(len(items) for items in MOBILITY_STRUCTURE.values())

    assert tuple(visitors.columns) == VISITOR_COLUMNS
    assert len(visitors) == subdestinations * 10
    assert not visitors.duplicated(["destination", "period"]).any()
    one = mobility.loc[
        (mobility["destino"] == "Panajachel") & (mobility["fecha"] == "2025-10-01"),
        "visitantes",
    ].sum()
    row = visitors.loc[
        (visitors["destination"] == "Panajachel") & (visitors["period"] == "2025-10-01")
    ]
    assert row["visitors"].item() == pytest.approx(one)


def test_months_without_coverage_are_absent_not_zero(mobility):
    visitors = subdestination_visitors(mobility)

    assert not visitors["period"].isin(pd.to_datetime(["2026-01-01", "2026-02-01"])).any()
    assert (visitors["visitors"] > 0).all()


def test_a_month_with_only_missing_visitors_stays_absent(mobility):
    blank = (mobility["destino"] == "Coban") & (mobility["fecha"] == "2026-03-01")
    mobility.loc[blank, "visitantes"] = float("nan")

    visitors = subdestination_visitors(mobility)

    coban = visitors.loc[visitors["destination"] == "Coban", "period"]
    assert pd.Timestamp("2026-03-01") not in set(coban)


def test_coverage_table_marks_each_source_by_month(config, mobility, migration):
    prepared = prepare(mobility, migration, config)
    coverage = prepared.coverage.set_index("period")

    assert coverage.loc["2025-09-01", "status"] == "ambas fuentes"
    assert coverage.loc["2026-01-01", "status"] == "solo entradas nacionales"
    assert coverage.loc["2026-02-01", "mobility"] == False  # noqa: E712
    assert coverage.loc["2026-08-01", "status"] == "solo movilidad"
    assert len(coverage) == 12


def test_coverage_table_reports_months_without_any_source(config):
    empty_visitors = pd.DataFrame(columns=VISITOR_COLUMNS)
    empty_entries = pd.DataFrame({"period": pd.to_datetime([]), "entries": []})

    coverage = coverage_table(empty_visitors, empty_entries, config)

    assert set(coverage["status"]) == {"sin cobertura"}


def test_factor_uses_only_fit_months_before_the_target(config, mobility, migration):
    prepared = prepare(mobility, migration, config)
    factors = reparto_factors(
        prepared.visitors, prepared.entries, config.periods.fit, pd.Timestamp("2026-01-01")
    )

    assert set(factors["months_used"]) == {4}
    assert set(factors["last_month"]) == {pd.Timestamp("2025-12-01")}
    visitors = prepared.visitors.set_index(["destination", "period"])["visitors"]
    entries = prepared.entries.set_index("period")["entries"]
    months = pd.date_range("2025-09-01", "2025-12-01", freq="MS")
    expected = sum(visitors["Coban", month] / entries[month] for month in months) / 4
    coban = factors.loc[factors["destination"] == "Coban", "factor"].item()
    assert coban == pytest.approx(expected)


def test_later_targets_include_more_fit_months(config, mobility, migration):
    prepared = prepare(mobility, migration, config)
    factors = reparto_factors(
        prepared.visitors, prepared.entries, config.periods.fit, pd.Timestamp("2026-05-01")
    )

    assert set(factors["months_used"]) == {6}


def test_factor_needs_fit_months_before_the_target(config, mobility, migration):
    prepared = prepare(mobility, migration, config)

    with pytest.raises(RepartoError, match="anteriores"):
        reparto_factors(
            prepared.visitors, prepared.entries, config.periods.fit, pd.Timestamp("2025-09-01")
        )


def test_zero_national_entries_cannot_be_a_denominator(config, mobility, migration):
    december = (migration["Año"] == 2025) & (migration["Mes cod"] == 12)
    migration.loc[december, "Viajero"] = 0.0
    prepared = prepare(mobility, migration, config)

    with pytest.raises(RepartoError, match="2025-12"):
        reparto_factors(
            prepared.visitors, prepared.entries, config.periods.fit, pd.Timestamp("2026-01-01")
        )
