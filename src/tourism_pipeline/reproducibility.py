from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from tourism_pipeline.config import PipelineConfig
from tourism_pipeline.pipeline import run_pipeline
from tourism_pipeline.tracking import record_reproducibility


VOLATILE_COLUMNS = {"run_id", "generated_at"}


@dataclass(frozen=True)
class ReproducibilityResult:
    equivalent: bool
    tolerance: float
    max_absolute_difference: float
    pipeline_run_ids: tuple[str, str]
    tracking_run_ids: tuple[str, str]
    compared_files: tuple[str, ...]


def _compare_frames(first: pd.DataFrame, second: pd.DataFrame, tolerance: float) -> tuple[bool, float]:
    columns = [column for column in first.columns if column not in VOLATILE_COLUMNS]
    if columns != [column for column in second.columns if column not in VOLATILE_COLUMNS]:
        return False, float("inf")
    first = first.loc[:, columns].sort_values(columns, kind="stable").reset_index(drop=True)
    second = second.loc[:, columns].sort_values(columns, kind="stable").reset_index(drop=True)
    if first.shape != second.shape:
        return False, float("inf")
    maximum = 0.0
    for column in columns:
        if pd.api.types.is_numeric_dtype(first[column]) and pd.api.types.is_numeric_dtype(second[column]):
            left = first[column].to_numpy(dtype=float)
            right = second[column].to_numpy(dtype=float)
            difference = np.abs(left - right)
            if difference.size:
                maximum = max(maximum, float(np.nanmax(difference)))
            if not np.allclose(left, right, rtol=0.0, atol=tolerance, equal_nan=True):
                return False, maximum
        elif not first[column].equals(second[column]):
            return False, float("inf")
    return True, maximum


def check_reproducibility(config: PipelineConfig) -> ReproducibilityResult:
    tolerance = config.tracking.reproducibility_tolerance
    with tempfile.TemporaryDirectory(prefix="pipeline-reproducibility-") as temporary:
        root = Path(temporary)
        first_config = replace(config, paths=replace(config.paths, output_dir=root / "first"))
        second_config = replace(config, paths=replace(config.paths, output_dir=root / "second"))
        first_run = run_pipeline(first_config)
        second_run = run_pipeline(second_config)
        equivalent = True
        maximum = 0.0
        compared_files = tuple(path.name for path in first_run.files.values())
        for key, first_path in first_run.files.items():
            second_path = second_run.files[key]
            matches, difference = _compare_frames(
                pd.read_csv(first_path),
                pd.read_csv(second_path),
                tolerance,
            )
            equivalent = equivalent and matches
            maximum = max(maximum, difference)

    tracking_ids = (first_run.tracking_run_id, second_run.tracking_run_id)
    record_reproducibility(config, tracking_ids, equivalent, maximum)
    return ReproducibilityResult(
        equivalent=equivalent,
        tolerance=tolerance,
        max_absolute_difference=maximum,
        pipeline_run_ids=(first_run.run_id, second_run.run_id),
        tracking_run_ids=tracking_ids,
        compared_files=compared_files,
    )
