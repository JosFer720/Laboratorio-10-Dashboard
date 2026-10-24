from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from tourism_dashboard.data import load_model_metrics, load_model_predictions
from tourism_dashboard.figures import model_errors_figure, model_evaluation_figure
from tourism_dashboard.models import (
    comparison_rows,
    metric_values,
    model_errors,
    model_options,
    model_status,
    sanitize_model_selection,
    selected_model_rows,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _artifacts() -> tuple[pd.DataFrame, pd.DataFrame]:
    predictions = load_model_predictions(DATA_DIR / "model_predictions_s0.csv")
    metrics = load_model_metrics(DATA_DIR / "model_metrics_s0.csv")
    return predictions, metrics


def test_model_options_follow_validated_artifact_order() -> None:
    predictions, metrics = _artifacts()

    assert model_options(predictions, metrics) == [
        {"label": "LSTM catch22 (ventana 24)", "value": "lstm-catch22-contexto-w24"},
        {"label": "Prophet", "value": "prophet"},
        {"label": "ARIMA(1,1,1)", "value": "arima-1-1-1"},
    ]


def test_model_selection_keeps_only_a_common_model_id() -> None:
    predictions, metrics = _artifacts()

    assert sanitize_model_selection("prophet", predictions, metrics) == {
        "model": "prophet"
    }
    assert sanitize_model_selection("desconocido", predictions, metrics) == {
        "model": None
    }
    assert sanitize_model_selection(None, predictions, metrics) == {"model": None}


def test_selected_model_rows_and_metrics_are_safe_for_empty_state() -> None:
    predictions, metrics = _artifacts()
    selection = {"model": "lstm-catch22-contexto-w24"}
    selected_predictions, selected_metrics = selected_model_rows(
        predictions, metrics, selection
    )

    assert len(selected_predictions) == 63
    assert len(selected_metrics) == 1
    assert metric_values(selected_metrics) == ("55.256", "67.735", "29,2 %")
    assert "LSTM catch22" in model_status(selected_metrics)
    assert "evaluación histórica" in model_status(selected_metrics)

    empty_predictions, empty_metrics = selected_model_rows(
        predictions, metrics, {"model": "desconocido"}
    )
    assert empty_predictions.empty
    assert empty_metrics.empty
    assert metric_values(empty_metrics) == ("—", "—", "—")
    assert model_status(empty_metrics) == "No hay un modelo válido seleccionado."


def test_model_figure_compares_observed_and_estimated_without_interval() -> None:
    predictions, metrics = _artifacts()
    selected, _ = selected_model_rows(predictions, metrics, {"model": "prophet"})

    figure = model_evaluation_figure(selected)

    assert [trace.name for trace in figure.data] == ["Observado", "Estimado · Prophet"]
    assert figure.data[0].line.color == "#0B5C8E"
    assert figure.data[0].line.dash == "solid"
    assert figure.data[1].line.color == "#D55E00"
    assert figure.data[1].line.dash == "dash"
    assert min(figure.data[0].x) == pd.Timestamp("2021-04-01")
    assert max(figure.data[0].x) == pd.Timestamp("2026-06-01")
    assert float(figure.data[0].y[0]) == 59_743.1902214643
    assert not any("interval" in str(trace.name).lower() for trace in figure.data)


def test_model_figure_has_a_clear_empty_state() -> None:
    figure = model_evaluation_figure(pd.DataFrame())

    assert not figure.data
    assert "No hay resultados" in figure.layout.annotations[0].text


@pytest.mark.parametrize(
    "model_id", ["lstm-catch22-contexto-w24", "prophet", "arima-1-1-1"]
)
def test_errors_use_original_estimates_without_mutating_them(model_id):
    predictions, metrics = _artifacts()
    selected, _ = selected_model_rows(predictions, metrics, {"model": model_id})
    original = selected.copy(deep=True)
    rows = model_errors(selected)
    figure = model_errors_figure(selected)

    assert rows["error"].tolist() == pytest.approx(
        (original["estimate"] - original["observed"]).tolist()
    )
    assert list(figure.data[0].y) == pytest.approx(rows["error"].tolist())
    assert len(figure.data[0].x) == 63
    assert figure.data[0].marker.color == "#D55E00"
    assert figure.layout.shapes[0].y0 == 0
    pd.testing.assert_frame_equal(selected, original)


def test_comparison_keeps_all_three_original_metrics():
    _, metrics = _artifacts()
    rows = comparison_rows(metrics)
    source = pd.read_csv(DATA_DIR / "model_metrics_s0.csv")
    assert len(rows) == 3
    for actual, expected in zip(rows, source.to_dict("records")):
        assert actual["model_id"] == expected["model_id"]
        assert actual["model_label"] == expected["model_label"]
        for metric in ("mae", "rmse", "mape"):
            assert actual[metric] == expected[metric]


def test_comparison_and_error_chart_support_missing_artifacts():
    predictions, metrics = _artifacts()
    assert comparison_rows(metrics.iloc[:0]) == []
    assert not model_errors_figure(predictions.iloc[:0]).data
