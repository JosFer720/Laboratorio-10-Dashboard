from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.estimation import error_metrics, evaluate_procedure
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.preparation import PreparedData, prepare
from tourism_pipeline.synthetic import MOBILITY_STRUCTURE, build_migration, build_mobility


SUBDESTINATIONS = sum(len(items) for items in MOBILITY_STRUCTURE.values())


@pytest.fixture
def config(tmp_path: Path):
    return load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.fixture
def prepared(config) -> PreparedData:
    mobility = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in build_mobility().items()],
        ignore_index=True,
    )
    return prepare(mobility, build_migration(), config)


def test_evaluates_march_to_june_in_order_and_never_uncovered_months(config, prepared):
    result = evaluate_procedure(prepared, config)

    assert result.evaluated_months == tuple(pd.date_range("2026-03-01", "2026-06-01", freq="MS"))
    assert len(result.predictions) == SUBDESTINATIONS * 4
    assert not result.predictions["period"].isin(pd.to_datetime(["2026-01-01", "2026-02-01"])).any()


def test_future_months_do_not_change_the_estimate_of_an_earlier_month(config, prepared):
    before = evaluate_procedure(prepared, config).predictions
    later = prepared.visitors["period"] > pd.Timestamp("2026-04-01")
    changed_visitors = prepared.visitors.assign(
        visitors=np.where(later, prepared.visitors["visitors"] * 50, prepared.visitors["visitors"])
    )
    changed = PreparedData(changed_visitors, prepared.entries, prepared.coverage)

    after = evaluate_procedure(changed, config).predictions

    april = before["period"] <= pd.Timestamp("2026-04-01")
    columns = ["candidate", "last_observed", "historical_mean"]
    pd.testing.assert_frame_equal(
        before.loc[april, columns].reset_index(drop=True),
        after.loc[after["period"] <= pd.Timestamp("2026-04-01"), columns].reset_index(drop=True),
    )


def test_hiding_a_month_uses_only_earlier_months_for_every_method(config, prepared):
    result = evaluate_procedure(prepared, config)
    row = result.predictions.loc[
        (result.predictions["destination"] == "Coban")
        & (result.predictions["period"] == pd.Timestamp("2026-03-01"))
    ].iloc[0]
    visitors = prepared.visitors.loc[prepared.visitors["destination"] == "Coban"].set_index("period")[
        "visitors"
    ]
    entries = prepared.entries.set_index("period")["entries"]
    earlier = pd.date_range("2025-09-01", "2025-12-01", freq="MS")

    factor = np.mean([visitors[month] / entries[month] for month in earlier])
    assert row["candidate"] == pytest.approx(factor * entries[pd.Timestamp("2026-03-01")])
    assert row["last_observed"] == pytest.approx(visitors[pd.Timestamp("2025-12-01")])
    assert row["historical_mean"] == pytest.approx(visitors[earlier].mean())
    assert row["observed"] == pytest.approx(visitors[pd.Timestamp("2026-03-01")])


def test_error_metrics_are_computed_on_the_same_rows():
    observed = pd.Series([100.0, 200.0, 400.0])
    predicted = pd.Series([110.0, 180.0, 400.0])

    metrics = error_metrics(observed, predicted)

    assert metrics["mae"] == pytest.approx(10.0)
    assert metrics["rmse"] == pytest.approx(np.sqrt((100 + 400) / 3))
    assert metrics["mape"] == pytest.approx((10 + 10 + 0) / 3)


def test_mape_skips_observed_zeros_and_counts_them():
    metrics = error_metrics(pd.Series([0.0, 100.0]), pd.Series([5.0, 90.0]))

    assert metrics["mape"] == pytest.approx(10.0)
    assert metrics["zero_observed_excluded"] == 1
    assert metrics["mae"] == pytest.approx(7.5)


def test_all_methods_are_summarized_by_subdestination(config, prepared):
    result = evaluate_procedure(prepared, config)

    summary = result.by_destination
    assert set(summary["method"]) == {"candidate", "last_observed", "historical_mean"}
    assert len(summary) == SUBDESTINATIONS * 3
    assert set(summary["months"]) == {4}
    flat = result.flat_metrics()
    assert flat["evaluated_months"] == 4
    assert {"candidate.mae", "last_observed.rmse", "historical_mean.mape"} <= set(flat)


def test_a_month_without_observations_is_skipped_not_scored(config, prepared):
    without_may = prepared.visitors.loc[prepared.visitors["period"] != pd.Timestamp("2026-05-01")]
    partial = PreparedData(without_may, prepared.entries, prepared.coverage)

    result = evaluate_procedure(partial, config)

    assert pd.Timestamp("2026-05-01") in result.skipped_months
    assert pd.Timestamp("2026-05-01") not in set(result.predictions["period"])
