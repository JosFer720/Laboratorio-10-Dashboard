from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tourism_pipeline.config import load_config
from tourism_pipeline.estimation import estimate_uncovered_months, evaluate_procedure
from tourism_pipeline.ingestion import SHEET_COLUMN
from tourism_pipeline.preparation import prepare
from tourism_pipeline.publication import decide_acceptance
from tourism_pipeline.synthetic import build_migration, build_mobility
from tourism_pipeline.validation import (
    ControlResult,
    ControlStatus,
    QualityReport,
    Severity,
)


NOW = datetime(2026, 10, 30, tzinfo=timezone.utc)


def _report(failed: bool = False) -> QualityReport:
    status = ControlStatus.FAILED if failed else ControlStatus.PASSED
    severity = Severity.CRITICAL if failed else Severity.WARNING
    result = ControlResult("uniqueness", "Unicidad", status, severity, "", {}, "", "")
    return QualityReport("run-1", NOW, (result,))


@pytest.fixture
def config(tmp_path: Path):
    return load_config(env={"INGUAT_DATA_DIR": str(tmp_path)})


@pytest.fixture
def candidate(config):
    mobility = pd.concat(
        [frame.assign(**{SHEET_COLUMN: sheet}) for sheet, frame in build_mobility().items()],
        ignore_index=True,
    )
    prepared = prepare(mobility, build_migration(), config)
    results = estimate_uncovered_months(prepared, config, "run-1", NOW).results
    evaluation = evaluate_procedure(prepared, config)
    return results, evaluation, prepared.visitors["destination"].unique()


def test_healthy_candidate_is_approved(config, candidate):
    results, evaluation, destinations = candidate

    decision = decide_acceptance(_report(), results, evaluation, destinations, config)

    assert decision.approved
    assert decision.verdict == "aprobada"
    assert decision.reasons == ()
    assert [check.name for check in decision.checks] == [
        "quality",
        "integrity",
        "evaluation_coverage",
        "performance",
    ]


def test_candidate_above_the_error_threshold_is_rejected_for_performance(config, candidate):
    results, evaluation, destinations = candidate
    strict = replace(config, acceptance=replace(config.acceptance, max_mape=0.1))

    decision = decide_acceptance(_report(), results, evaluation, destinations, strict)

    assert not decision.approved
    assert decision.verdict == "rechazada"
    assert len(decision.reasons) == 1
    assert "MAPE" in decision.reasons[0]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda frame: frame.assign(value=np.where(frame.index == 0, -5.0, frame["value"])), "negativas"),
        (lambda frame: frame.assign(value=np.where(frame.index == 0, 0.0, frame["value"])), "en cero"),
        (lambda frame: frame.assign(value=np.where(frame.index == 0, np.inf, frame["value"])), "no finitos"),
        (lambda frame: frame.loc[frame["period"] != pd.Timestamp("2026-02-01")], "faltan"),
        (lambda frame: frame.drop(columns="run_id"), "columnas"),
        (lambda frame: frame.assign(kind="observed"), "rotuladas"),
    ],
)
def test_incomplete_outputs_are_rejected_for_integrity(config, candidate, change, message):
    results, evaluation, destinations = candidate

    decision = decide_acceptance(_report(), change(results), evaluation, destinations, config)

    assert not decision.approved
    integrity = next(check for check in decision.checks if check.name == "integrity")
    assert not integrity.passed
    assert message in integrity.message


def test_a_critical_quality_failure_rejects_the_candidate(config, candidate):
    results, evaluation, destinations = candidate

    decision = decide_acceptance(_report(failed=True), results, evaluation, destinations, config)

    assert not decision.approved
    assert "uniqueness" in decision.reasons[0]


def test_too_few_evaluated_months_rejects_the_candidate(config, candidate):
    results, evaluation, destinations = candidate
    short = replace(evaluation, evaluated_months=evaluation.evaluated_months[:2])

    decision = decide_acceptance(_report(), results, short, destinations, config)

    assert not decision.approved
    assert any("al menos 4" in reason for reason in decision.reasons)


def test_decision_record_keeps_verdict_reasons_and_thresholds(config, candidate):
    results, evaluation, destinations = candidate

    record = decide_acceptance(_report(), results, evaluation, destinations, config).as_record()

    assert record["verdict"] == "aprobada"
    assert record["thresholds"] == {"max_mape": 25.0, "min_evaluated_months": 4.0}
    assert len(record["checks"]) == 4
