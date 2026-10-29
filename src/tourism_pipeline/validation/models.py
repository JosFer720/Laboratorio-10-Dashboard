from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class ControlStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class Severity(str, Enum):
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ControlResult:
    name: str
    description: str
    status: ControlStatus
    severity: Severity
    message: str
    detail: dict[str, Any]
    warning_condition: str
    stop_condition: str

    @property
    def stops_pipeline(self) -> bool:
        return self.status is ControlStatus.FAILED and self.severity is Severity.CRITICAL

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["status"] = self.status.value
        record["severity"] = self.severity.value
        return record


@dataclass(frozen=True)
class QualityReport:
    run_id: str
    generated_at: datetime
    results: tuple[ControlResult, ...]
    path: Path | None = None

    @property
    def has_critical_failures(self) -> bool:
        return any(result.stops_pipeline for result in self.results)


class QualityControlError(RuntimeError):
    """Uno o más controles críticos fallaron después de escribir el reporte."""

    def __init__(self, report: QualityReport):
        self.report = report
        failures = [result.name for result in report.results if result.stops_pipeline]
        super().__init__("Fallaron controles críticos: " + ", ".join(failures))


@dataclass(frozen=True)
class MethodologyContext:
    mobility_source: str = "monthly"
    aggregates_subdestinations: bool = False


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
