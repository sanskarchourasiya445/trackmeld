"""TrackMeld Independent Validation and Diagnostics Package (Phase 7).

Provides independent post-solve auditing, safety gating, root-cause diagnostics,
and controlled relaxation analysis for railway maintenance schedules.
"""

from backend.app.services.validation.models import (
    ValidationStatus,
    ValidationSeverity,
    ValidationCategory,
    ValidationFinding,
    ScheduleValidationResult,
    DiagnosticStatus,
    RelaxationScenarioType,
    RelaxationFinding,
    UnscheduledTaskDiagnostic,
    DiagnosticsReport,
)
from backend.app.services.validation.exceptions import (
    ValidationException,
    ValidationExecutionError,
    ScheduleApprovalBlockedError,
)
from backend.app.services.validation.checks import ScheduleCheckRunner
from backend.app.services.validation.validator import IndependentScheduleValidator
from backend.app.services.validation.relaxation import RelaxationAnalyzer
from backend.app.services.validation.diagnostics import UnscheduledTaskDiagnosticsService


def validate_schedule(snapshot, schedule) -> ScheduleValidationResult:
    """Convenience functional interface for schedule validation."""
    return IndependentScheduleValidator.validate(snapshot, schedule)


def assert_schedule_approvable(snapshot, schedule) -> ScheduleValidationResult:
    """Convenience functional interface enforcing the approval gate."""
    return IndependentScheduleValidator.assert_schedule_approvable(snapshot, schedule)


__all__ = [
    "ValidationStatus",
    "ValidationSeverity",
    "ValidationCategory",
    "ValidationFinding",
    "ScheduleValidationResult",
    "DiagnosticStatus",
    "RelaxationScenarioType",
    "RelaxationFinding",
    "UnscheduledTaskDiagnostic",
    "DiagnosticsReport",
    "ValidationException",
    "ValidationExecutionError",
    "ScheduleApprovalBlockedError",
    "ScheduleCheckRunner",
    "IndependentScheduleValidator",
    "RelaxationAnalyzer",
    "UnscheduledTaskDiagnosticsService",
    "validate_schedule",
    "assert_schedule_approvable",
]
